"""
模式10: 自动录屏 (热键控制 + 阵容拼接版)
自动截取双方阵容，模拟热键录制对局，并将阵容图拼接到视频开头。
"""
from core import utils as core_utils
from core import constants as core_constants
import os
import datetime
import time
import cv2
import numpy as np
import pyautogui
import shutil
import glob
import subprocess


class ExternalRecorderController:
    """外部录屏软件控制器 (热键方案)"""
    
    def __init__(self, context):
        self.context = context
        self.logger = context.shared.logger
        
        # 从 app_config 中获取模式10的专用配置
        m10_config = context.shared.app_config.get('mode_10', {})
        
        self.start_hotkey = m10_config.get('m10_start_hotkey', 'alt+f9').lower().split('+')
        self.stop_hotkey = m10_config.get('m10_stop_hotkey', 'alt+f9').lower().split('+')
        self.source_dir = m10_config.get('m10_source_dir', '')
        self.target_dir = m10_config.get('m10_target_dir', '')
        
        self.is_recording = False

    def start_recording(self):
        if self.is_recording: return
        self.logger.info(f"触发开始录制热键: {'+'.join(self.start_hotkey)}")
        pyautogui.hotkey(*self.start_hotkey)
        self.is_recording = True
        return True

    def stop_recording(self):
        if not self.is_recording: return
        self.logger.info(f"触发停止录制热键: {'+'.join(self.stop_hotkey)}")
        pyautogui.hotkey(*self.stop_hotkey)
        self.is_recording = False
        return True

    def get_latest_video(self):
        """获取源目录下最新的视频文件"""
        if not self.source_dir or not os.path.exists(self.source_dir):
            return None
        video_extensions = ['*.mp4', '*.mkv', '*.mov', '*.flv', '*.ts']
        all_videos = []
        for ext in video_extensions:
            all_videos.extend(glob.glob(os.path.join(self.source_dir, ext)))
        if not all_videos: return None
        return max(all_videos, key=os.path.getmtime)


def capture_lineup(context, window, side='left', team_idx=0):
    """
    截取指定玩家的指定队伍阵容图
    """
    logger = context.shared.logger
    # 坐标定义 (参考 core/constants.py)
    entry_coord = core_constants.R_PLAYER1_ENTRY_REL if side == 'left' else core_constants.R_PLAYER2_ENTRY_REL
    team_btns = core_constants.R_TEAM_BUTTONS_REL
    screenshot_region = core_constants.R_TEAM_SCREENSHOT_REGION_REL
    exit_coord = core_constants.R_CLOSE_RESULT_REL # 借用关闭按钮坐标
    
    logger.info(f"正在截取 {side} 玩家第 {team_idx+1} 队阵容...")
    
    # 1. 进入玩家信息
    core_utils.click_coordinates(context, entry_coord, window)
    time.sleep(2.0)
    
    # 2. 点击对应队伍按钮
    if team_idx < len(team_btns):
        core_utils.click_coordinates(context, team_btns[team_idx], window)
        time.sleep(1.0)
    
    # 3. 截图
    timestamp = int(time.time() * 1000)
    save_path = os.path.join(context.shared.base_temp_dir, f"lineup_{side}_{team_idx}_{timestamp}.png")
    core_utils.take_screenshot(context, screenshot_region, window, save_path)
    
    # 4. 退出界面
    core_utils.click_coordinates(context, exit_coord, window)
    time.sleep(1.0)
    
    return save_path


def process_video_with_lineup(context, video_path, left_img, right_img, match_index):
    """
    使用 FFmpeg 将阵容图拼接到视频开头
    """
    logger = context.shared.logger
    ffmpeg_exe = os.path.join(os.getcwd(), "ffmpeg.exe")
    if not os.path.exists(ffmpeg_exe):
        logger.error("未找到 ffmpeg.exe，跳过后期合成。")
        return video_path

    target_dir = context.shared.app_config.get('mode_10', {}).get('m10_target_dir', '')
    if not target_dir: return video_path
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    final_output = os.path.join(target_dir, f"match_{match_index+1}_{timestamp}_full.mp4")
    
    # 1. 合成阵容对比图 (1920x1080 背景)
    lineup_bg = os.path.join(context.shared.base_temp_dir, f"lineup_bg_{match_index}.png")
    bg = np.zeros((1080, 1920, 3), dtype=np.uint8)
    
    img_l = cv2.imread(left_img)
    img_r = cv2.imread(right_img)
    
    if img_l is not None and img_r is not None:
        # 缩放图片以适应半屏
        h, w = 400, 800 # 预设尺寸
        img_l = cv2.resize(img_l, (w, h))
        img_r = cv2.resize(img_r, (w, h))
        # 放置位置
        bg[340:340+h, 100:100+w] = img_l
        bg[340:340+h, 1020:1020+w] = img_r
        # 画个 VS 文本 (可选)
        cv2.putText(bg, "VS", (910, 560), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
        cv2.imwrite(lineup_bg, bg)
    else:
        logger.error("读取阵容截图失败，跳过合成。")
        return video_path

    # 2. FFmpeg 合成指令: [阵容图2秒] + [原视频]
    # 使用 filter_complex 实现无缝拼接
    cmd = [
        ffmpeg_exe, "-y",
        "-loop", "1", "-t", "2", "-i", lineup_bg,
        "-i", video_path,
        "-filter_complex", "[0:v]format=yuv420p[v0];[1:v]scale=1920:1080,format=yuv420p[v1];[v0][v1]concat=n=2:v=1:a=0[outv]",
        "-map", "[outv]", "-map", "1:a?", # 尝试保留原视频音频
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        final_output
    ]
    
    try:
        logger.info(f"正在合成最终视频: {os.path.basename(final_output)}")
        subprocess.run(cmd, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        logger.info("合成完成！")
        # 清理临时文件和原视频
        if os.path.exists(video_path): os.remove(video_path)
        return final_output
    except Exception as e:
        logger.error(f"FFmpeg 合成失败: {e}")
        return video_path


def detect_win_screen(context, window):
    try:
        win_region_rel = (0.4, 0.1, 0.2, 0.15)
        stats_icon_region_rel = (0.6, 0.9, 0.05, 0.08)
        temp_win_path = os.path.join(context.shared.base_temp_dir, "check_win.png")
        core_utils.take_screenshot(context, win_region_rel, window, temp_win_path)
        
        is_win = False
        if os.path.exists(temp_win_path):
            img = cv2.imread(temp_win_path)
            if img is not None:
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                blue_mask = (img_rgb[:,:,0] < 100) & (img_rgb[:,:,1] > 180) & (img_rgb[:,:,2] > 180)
                red_mask = (img_rgb[:,:,0] > 200) & (img_rgb[:,:,1] < 100) & (img_rgb[:,:,2] < 100)
                if np.sum(blue_mask) / img_rgb.size > 0.01 or np.sum(red_mask) / img_rgb.size > 0.01:
                    is_win = True
            os.remove(temp_win_path)
        return is_win
    except: return False


def record_single_match(context, window, match_index):
    logger = context.shared.logger
    logger.info(f"===== 开始处理 Round {match_index + 1:02d} =====")
    
    recorder = ExternalRecorderController(context)
    
    # 1. 战前侦察：截图阵容
    left_img = capture_lineup(context, window, 'left', match_index)
    right_img = capture_lineup(context, window, 'right', match_index)
    
    # 2. 点击播放并开始录制
    play_coords = [(0.6057, 0.5850), (0.6057, 0.6247), (0.6057, 0.6652), (0.6057, 0.7064), (0.6057, 0.7462)]
    core_utils.click_coordinates(context, play_coords[match_index], window)
    time.sleep(3.0)
    recorder.start_recording()
    
    # 3. 监控结算
    start_time = time.time()
    while time.time() - start_time < 600:
        if core_utils.check_stop_signal(context): break
        if detect_win_screen(context, window):
            time.sleep(3.0)
            core_utils.click_coordinates(context, (0.6284, 0.9465), window) # 统计按钮
            time.sleep(3.0)
            break
        time.sleep(1.0)
    
    # 4. 停止并处理
    recorder.stop_recording()
    time.sleep(3.0)
    raw_video = recorder.get_latest_video()
    
    if raw_video:
        process_video_with_lineup(context, raw_video, left_img, right_img, match_index)
    
    # 5. 退出
    exit_rel = (0.8428, 0.5401)
    for _ in range(2):
        core_utils.click_coordinates(context, exit_rel, window)
        time.sleep(1.5)
    return True


def run(context):
    logger = context.shared.logger
    window = core_utils.find_and_activate_window(context)
    if not window: return
    
    m10_config = context.shared.app_config.get('mode_10', {})
    match_count = m10_config.get('m10_match_count', 5)
    start_idx = m10_config.get('m10_start_index', 0)
    
    for i in range(start_idx, start_idx + match_count):
        if core_utils.check_stop_signal(context): break
        record_single_match(context, window, i)
    logger.info("===== 模式 10 执行完毕 =====")
