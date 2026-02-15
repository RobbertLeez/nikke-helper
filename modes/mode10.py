"""
模式10: 自动录屏 (热键控制方案)
自动点击播放按钮，通过模拟热键触发外部录屏软件（如 OBS, NVIDIA ShadowPlay），
并在录制结束后自动定位最新视频文件并搬运到目标目录。
"""
from core import utils as core_utils
import os
import datetime
import time
import cv2
import numpy as np
import pyautogui
import win32gui
import shutil
import glob


class ExternalRecorderController:
    """外部录屏软件控制器 (热键方案)"""
    
    def __init__(self, context):
        self.context = context
        self.logger = context.shared.logger
        
        # 从 app_config 中获取模式10的专用配置
        m10_config = context.shared.app_config.get('mode_10', {})
        
        # 热键格式如: ['alt', 'f9'] 或 ['f10']
        self.start_hotkey = m10_config.get('m10_start_hotkey', 'alt+f9').lower().split('+')
        self.stop_hotkey = m10_config.get('m10_stop_hotkey', 'alt+f9').lower().split('+')
        self.source_dir = m10_config.get('m10_source_dir', '')
        self.target_dir = m10_config.get('m10_target_dir', '')
        
        self.is_recording = False

    def start_recording(self):
        """模拟热键开始录制"""
        if self.is_recording:
            return
        
        self.logger.info(f"触发开始录制热键: {'+'.join(self.start_hotkey)}")
        pyautogui.hotkey(*self.start_hotkey)
        self.is_recording = True
        return True

    def stop_recording(self):
        """模拟热键停止录制"""
        if not self.is_recording:
            return
        
        self.logger.info(f"触发停止录制热键: {'+'.join(self.stop_hotkey)}")
        pyautogui.hotkey(*self.stop_hotkey)
        self.is_recording = False
        return True

    def capture_and_move_video(self, match_index):
        """
        在录制停止后，从源目录找到最新的视频文件并搬运到目标目录
        """
        if not self.source_dir or not os.path.exists(self.source_dir):
            self.logger.error(f"源目录不存在或未设置: {self.source_dir}")
            return None
        
        if not self.target_dir:
            self.logger.error("目标目录未设置")
            return None
            
        if not os.path.exists(self.target_dir):
            os.makedirs(self.target_dir, exist_ok=True)

        # 给录屏软件留出写文件和封口的时间
        self.logger.info("等待录屏软件完成文件写入 (3秒)...")
        time.sleep(3.0)

        # 查找源目录下最新的视频文件 (mp4, mkv, mov, flv)
        video_extensions = ['*.mp4', '*.mkv', '*.mov', '*.flv', '*.ts']
        all_videos = []
        for ext in video_extensions:
            all_videos.extend(glob.glob(os.path.join(self.source_dir, ext)))
        
        if not all_videos:
            self.logger.warning(f"在源目录 {self.source_dir} 中未找到任何视频文件")
            return None
            
        # 按修改时间排序，取最新的
        latest_video = max(all_videos, key=os.path.getmtime)
        
        # 检查文件是否是刚刚生成的 (1分钟内)
        file_age = time.time() - os.path.getmtime(latest_video)
        if file_age > 60:
            self.logger.warning(f"找到的最新的视频文件过旧 ({int(file_age)}秒前)，可能不是本次录制的。")
            return None

        # 准备目标路径
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = os.path.splitext(latest_video)[1]
        new_filename = f"match_{match_index + 1}_{timestamp}{ext}"
        target_path = os.path.join(self.target_dir, new_filename)

        try:
            self.logger.info(f"正在搬运视频: {os.path.basename(latest_video)} -> {new_filename}")
            shutil.move(latest_video, target_path)
            self.logger.info(f"视频搬运成功: {target_path}")
            return target_path
        except Exception as e:
            self.logger.error(f"搬运视频失败: {e}")
            return None


def detect_win_screen(context, window):
    """
    多重特征校验检测结算界面
    """
    logger = context.shared.logger
    try:
        win_region_rel = (0.4, 0.1, 0.2, 0.15)
        stats_icon_region_rel = (0.6, 0.9, 0.05, 0.08)
        
        temp_win_path = os.path.join(context.shared.base_temp_dir, f"check_win_{int(time.time())}.png")
        temp_stats_path = os.path.join(context.shared.base_temp_dir, f"check_stats_{int(time.time())}.png")
        
        core_utils.take_screenshot(context, win_region_rel, window, temp_win_path)
        core_utils.take_screenshot(context, stats_icon_region_rel, window, temp_stats_path)
        
        is_win = False
        win_type = None
        
        if os.path.exists(temp_win_path):
            img = cv2.imread(temp_win_path)
            if img is not None:
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                blue_mask = (img_rgb[:,:,0] < 100) & (img_rgb[:,:,1] > 180) & (img_rgb[:,:,2] > 180)
                red_mask = (img_rgb[:,:,0] > 200) & (img_rgb[:,:,1] < 100) & (img_rgb[:,:,2] < 100)
                blue_ratio = np.sum(blue_mask) / img_rgb.size
                red_ratio = np.sum(red_mask) / img_rgb.size
                if blue_ratio > 0.01:
                    is_win = True
                    win_type = 'blue'
                elif red_ratio > 0.01:
                    is_win = True
                    win_type = 'red'
            os.remove(temp_win_path)

        has_stats_icon = False
        if is_win and os.path.exists(temp_stats_path):
            img_stats = cv2.imread(temp_stats_path)
            if img_stats is not None:
                gray = cv2.cvtColor(img_stats, cv2.COLOR_BGR2GRAY)
                bright_pixels = np.sum(gray > 150) / gray.size
                edges = cv2.Canny(gray, 50, 150)
                edge_density = np.sum(edges > 0) / edges.size
                if bright_pixels > 0.01 or edge_density > 0.01: 
                    has_stats_icon = True
            os.remove(temp_stats_path)
        
        if is_win and has_stats_icon:
            logger.info(f"【精准命中】检测到结算界面: {win_type}")
            return (True, win_type)
        return (False, None)
    except Exception as e:
        logger.error(f"检测结算界面时出错: {e}")
        return (False, None)


def click_play_button(context, window, button_index):
    play_button_coords_rel = [
        (0.6057, 0.5850), (0.6057, 0.6247), (0.6057, 0.6652), (0.6057, 0.7064), (0.6057, 0.7462),
    ]
    if button_index < 0 or button_index >= len(play_button_coords_rel):
        return False
    coord = play_button_coords_rel[button_index]
    return core_utils.click_coordinates(context, coord, window)


def click_stats_button(context, window):
    stats_button_coord_rel = (0.6284, 0.9465)
    return core_utils.click_coordinates(context, stats_button_coord_rel, window)


def record_single_match(context, window, match_index):
    logger = context.shared.logger
    logger.info(f"===== 开始处理 Round {match_index + 1:02d} =====")
    
    if core_utils.check_stop_signal(context):
        return None
    
    # 初始化外部录制控制器
    recorder = ExternalRecorderController(context)
    
    try:
        # 1. 点击播放按钮
        if not click_play_button(context, window, match_index):
            return False
        
        # 2. 触发开始录制
        logger.info("等待视频加载...")
        time.sleep(3.0)
        recorder.start_recording()
        
        # 3. 监控结算界面
        logger.info("开始监控结算界面...")
        win_detected = False
        start_time = time.time()
        max_wait_time = 600 # 最多等10分钟
        
        while time.time() - start_time < max_wait_time:
            if core_utils.check_stop_signal(context):
                recorder.stop_recording()
                return False
            
            detected, win_type = detect_win_screen(context, window)
            if detected:
                win_detected = True
                break
            time.sleep(1.0)
        
        # 4. 结算后处理
        if win_detected:
            logger.info("检测到结算，等待 3.0 秒动画结束...")
            time.sleep(3.0)
            click_stats_button(context, window)
            logger.info("已点击统计按钮，展示数据 3.0 秒...")
            time.sleep(3.0)
        
        # 5. 停止录制并搬运文件
        recorder.stop_recording()
        recorder.capture_and_move_video(match_index)
        
        # 6. 退出流程
        logger.info("退出当前对局...")
        exit_click_rel = (0.8428, 0.5401)
        core_utils.click_coordinates(context, exit_click_rel, window)
        time.sleep(1.5)
        core_utils.click_coordinates(context, exit_click_rel, window)
        time.sleep(2.0)
        
        return True
        
    except Exception as e:
        logger.error(f"录制过程出错: {e}")
        recorder.stop_recording()
        return False


def run(context):
    logger = context.shared.logger
    logger.info("===== 运行模式 10: 自动录屏 (热键搬运版) =====")
    
    window = core_utils.find_and_activate_window(context)
    if not window:
        return
    
    # 从 app_config 中获取模式10的专用配置
    m10_config = context.shared.app_config.get('mode_10', {})
    match_count = m10_config.get('m10_match_count', 5)
    start_index = m10_config.get('m10_start_index', 0)
    
    for i in range(start_index, start_index + match_count):
        if core_utils.check_stop_signal(context):
            break
        
        success = record_single_match(context, window, i)
        if not success:
            logger.warning(f"Round {i+1} 处理失败，尝试下一局")
            continue
            
    logger.info("===== 模式 10 执行完毕 =====")
