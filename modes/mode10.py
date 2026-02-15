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
        m10_config = context.shared.app_config.get("mode_10", {})
        
        self.start_hotkey = m10_config.get("m10_start_hotkey", "alt+f9").lower().split("+")
        self.stop_hotkey = m10_config.get("m10_stop_hotkey", "alt+f9").lower().split("+")
        self.source_dir = m10_config.get("m10_source_dir", "")
        self.target_dir = m10_config.get("m10_target_dir", "")
        
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
        video_extensions = ["*.mp4", "*.mkv", "*.mov", "*.flv", "*.ts"]
        all_videos = []
        for ext in video_extensions:
            all_videos.extend(glob.glob(os.path.join(self.source_dir, ext)))
        if not all_videos: return None
        return max(all_videos, key=os.path.getmtime)


def capture_lineup(context, window, side="left", team_idx=0):
    """
    截取指定玩家的指定队伍阵容图
    """
    logger = context.shared.logger
    # 坐标定义 (参考 core/constants.py)
    entry_coord = core_constants.R_PLAYER1_ENTRY_REL if side == "left" else core_constants.R_PLAYER2_ENTRY_REL
    team_btns = core_constants.R_TEAM_BUTTONS_REL
    # 用户提供的 2375x1336 分辨率下的新截图区域 (866, 503) 到 (1506, 986)
    # 用户提供的 2375x1336 分辨率下的新截图区域 (866, 503-43) 到 (1506, 986-43)
    # 转换为相对坐标: (x_rel, y_rel, width_rel, height_rel)
    # x_rel = 866 / 2375 = 0.3646
    # y_rel = (503 - 43) / 1336 = 460 / 1336 = 0.3443
    # width_rel = (1506 - 866) / 2375 = 640 / 2375 = 0.2695
    # height_rel = (986 - 503) / 1336 = 483 / 1336 = 0.3615
    screenshot_region = (0.3646, 0.3443, 0.2695, 0.3615)
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
    
    # 5. 识别玩家 ID (已移除 OCR)
    player_id = ""
    
    return save_path, player_id


def process_video_with_lineup(context, video_path, left_img, right_img, left_player_id, right_player_id, match_index, is_win=None):
    """
    使用 FFmpeg 将阵容图拼接到视频开头
    """
    logger = context.shared.logger
    ffmpeg_exe = os.path.join(os.getcwd(), "ffmpeg.exe")
    if not os.path.exists(ffmpeg_exe):
        logger.error("未找到 ffmpeg.exe，跳过后期合成。")
        return video_path

    target_dir = context.shared.app_config.get("mode_10", {}).get("m10_target_dir", "")
    if not target_dir: return video_path
    
    # 获取命名所需的配置信息
    m10_config = context.shared.app_config.get("mode_10", {})
    season = m10_config.get("m10_season", 1)
    match_stage = m10_config.get("m10_match_stage", "未知阶段")
    
    # 构建新的文件名 (仅显示日期，简化格式)
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    filename = f"S{season}_{match_stage}_Match{match_index+1}_{current_date}.mp4"
    
    # 按赛季创建子文件夹
    season_dir = os.path.join(target_dir, f"S{season}")
    if not os.path.exists(season_dir):
        os.makedirs(season_dir, exist_ok=True)
    
    final_output = os.path.join(season_dir, filename)
    
    # 1. 合成阵容对比图 (1920x1080 背景)
    lineup_bg_path = os.path.join(context.shared.base_temp_dir, f"lineup_bg_{match_index}.png")
    bg_width, bg_height = 1920, 1080
    bg = np.zeros((bg_height, bg_width, 3), dtype=np.uint8)
    
    img_l = cv2.imread(left_img)
    img_r = cv2.imread(right_img)
    
    if img_l is not None and img_r is not None:
        # 目标显示区域宽度 (例如，总宽度的一半减去一些间距)
        target_half_width = (bg_width - 100) // 2 # 100是左右总间距
        max_height = bg_height - 200 # 上下留白

        # 等比例缩放左图
        h_l, w_l, _ = img_l.shape
        scale_l = min(target_half_width / w_l, max_height / h_l)
        new_w_l, new_h_l = int(w_l * scale_l), int(h_l * scale_l)
        img_l_resized = cv2.resize(img_l, (new_w_l, new_h_l))

        # 等比例缩放右图
        h_r, w_r, _ = img_r.shape
        scale_r = min(target_half_width / w_r, max_height / h_r)
        new_w_r, new_h_r = int(w_r * scale_r), int(h_r * scale_r)
        img_r_resized = cv2.resize(img_r, (new_w_r, new_h_r))

        # 放置位置 (居中，并留出间距)
        # 左图起始X: (bg_width / 2 - 间距 - new_w_l) / 2
        # 右图起始X: bg_width / 2 + 间距 / 2
        spacing = 60 # 左右图之间的间距
        start_x_l = (bg_width // 2 - spacing // 2 - new_w_l) // 2 + 20 # 额外左边距
        start_y_l = (bg_height - new_h_l) // 2
        
        start_x_r = bg_width // 2 + spacing // 2 - 20 # 额外右边距
        start_y_r = (bg_height - new_h_r) // 2

        bg[start_y_l:start_y_l+new_h_l, start_x_l:start_x_l+new_w_l] = img_l_resized
        bg[start_y_r:start_y_r+new_h_r, start_x_r:start_x_r+new_w_r] = img_r_resized

        # 根据胜负添加 WIN 字样 (移除 VS)
        if is_win is not None:
            text = "WIN"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 3.0  # 增加为原来的 2 倍 (之前是 1.5)
            font_thickness = 6
            color = (0, 0, 255) # 红色
            
            # 精确坐标调整
            if is_win: # 左边赢
                win_pos = (535, 340)
            else: # 右边赢
                win_pos = (1470, 340)
            
            cv2.putText(bg, text, win_pos, font, font_scale, color, font_thickness)
        
        cv2.imwrite(lineup_bg_path, bg)
    else:
        logger.error("读取阵容截图失败，跳过合成。")
        return video_path

    # 2. FFmpeg 合成指令: [阵容图2秒] + [原视频]
    # 使用 filter_complex 实现无缝拼接，并添加静音音轨
    cmd = [
        ffmpeg_exe, "-y",
        "-loop", "1", "-t", "2", "-i", lineup_bg_path, # 2秒图片
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100", # 2秒静音音轨
        "-i", video_path,
        "-filter_complex", 
        "[0:v]format=yuv420p,setsar=1[v0];" # 阵容图视频流
        "[1:a]atrim=duration=2[a0];" # 2秒静音音轨
        "[2:v]scale=1920:1080,format=yuv420p,setsar=1[v1];" # 原视频视频流
        "[2:a]anull[a1];" # 原视频音频流 (如果存在)
        "[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]", # 视频和音频流拼接
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        final_output
    ]
    
    try:
        logger.info(f"正在合成最终视频: {os.path.basename(final_output)}")
        subprocess.run(cmd, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        logger.info("合成完成！")
        # 清理临时文件和原视频
        if os.path.exists(video_path): os.remove(video_path)
        if os.path.exists(lineup_bg_path): os.remove(lineup_bg_path)
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
    # 获取模式10的配置，用于判断是否跳过当前对局
    m10_config = context.shared.app_config.get("mode_10", {})
    if not m10_config.get(f"m10_match_{match_index+1}_selected", False):
        context.shared.logger.info(f"对局 {match_index+1} 未被勾选，跳过录制。")
        return True


    logger = context.shared.logger
    logger.info(f"===== 开始处理 Round {match_index + 1:02d} =====")
    
    recorder = ExternalRecorderController(context)
    
    # 1. 战前侦察：截图阵容
    left_img, left_player_id = capture_lineup(context, window, "left", match_index)
    right_img, right_player_id = capture_lineup(context, window, "right", match_index)
    
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
    
    # 获取胜负结果
    is_win = detect_win_screen(context, window)
    
    if raw_video:
        process_video_with_lineup(context, raw_video, left_img, right_img, left_player_id, right_player_id, match_index, is_win=is_win)
    
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
    
    m10_config = context.shared.app_config.get("mode_10", {})
    match_count = m10_config.get("m10_match_count", 5)
    start_idx = m10_config.get("m10_start_index", 0)
    
    # 获取用户勾选的对局列表
    selected_matches = []
    for i in range(5):
        if m10_config.get(f"m10_match_{i+1}_selected", False):
            selected_matches.append(i)

    if not selected_matches:
        logger.warning("没有选择任何对局进行录制，模式10结束。")
        return

    for i in selected_matches:
        if core_utils.check_stop_signal(context): break
        record_single_match(context, window, i)
    logger.info("===== 模式 10 执行完毕 =====")
