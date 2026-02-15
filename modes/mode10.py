"""
模式10: 自动录屏
自动点击播放按钮，录制对局回放视频，检测WIN结果页面后点击统计按钮并停止录屏
"""
from core import utils as core_utils
import os
import datetime
import time
import cv2
import numpy as np
import pyautogui
import win32gui
from PIL import Image
import threading

# 尝试导入 dxcam，如果不可用则退回到 pyautogui 截图
try:
    import dxcam
    DXCAM_AVAILABLE = True
except ImportError:
    DXCAM_AVAILABLE = False


class VideoRecorder:
    """视频录制器类 (优先使用 DXGI 方案实现高性能录屏)"""
    
    def __init__(self, context, output_path, fps=60, resolution=(1920, 1080)):
        self.context = context
        self.logger = context.shared.logger
        self.output_path = output_path
        self.fps = fps
        self.resolution = resolution
        self.recording = False
        self.writer = None
        self.thread = None
        self.camera = None
        
        if DXCAM_AVAILABLE:
            try:
                # 初始化 dxcam 实例
                self.camera = dxcam.create(output_color="BGR")
                self.logger.info("DXCAM 初始化成功，将使用 DXGI 高性能录屏方案")
            except Exception as e:
                self.logger.error(f"DXCAM 初始化失败: {e}，将回退到普通截图方案")
                self.camera = None

    def start_recording(self, window_hwnd):
        """开始录制指定窗口"""
        if self.recording:
            self.logger.warning("录制已在进行中")
            return False
            
        try:
            # 获取窗口客户区在屏幕上的位置
            left, top, right, bottom = win32gui.GetClientRect(window_hwnd)
            screen_left, screen_top = win32gui.ClientToScreen(window_hwnd, (left, top))
            width = right - left
            height = bottom - top
            
            # 记录录制区域
            self.capture_region = (screen_left, screen_top, screen_left + width, screen_top + height)
            self.logger.info(f"开始录制窗口区域: {self.capture_region}")
            
            # 初始化视频写入器
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.writer = cv2.VideoWriter(
                self.output_path,
                fourcc,
                self.fps,
                self.resolution
            )
            
            if not self.writer.isOpened():
                self.logger.error("无法创建视频写入器")
                return False
            
            self.recording = True
            
            # 启动录制线程
            self.thread = threading.Thread(target=self._recording_loop)
            self.thread.daemon = True
            self.thread.start()
            
            self.logger.info(f"录制已启动 (FPS: {self.fps})，输出文件: {self.output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"启动录制失败: {e}")
            return False
    
    def _recording_loop(self):
        """录制循环（在单独线程中运行）"""
        frame_interval = 1.0 / self.fps
        
        # 如果支持 DXCAM，使用其内置的高性能截图
        if self.camera:
            try:
                # 开启 DXCAM 录制
                # 注意：dxcam 的 region 格式是 (left, top, right, bottom)
                self.camera.start(region=self.capture_region, target_fps=self.fps)
                self.logger.info(f"DXCAM 录制循环已启动，目标 FPS: {self.fps}")
                
                while self.recording:
                    loop_start = time.time()
                    
                    # 获取最新帧 (dxcam 内部会处理帧率同步)
                    frame = self.camera.get_latest_frame()
                    
                    if frame is not None:
                        # 调整分辨率
                        if frame.shape[1] != self.resolution[0] or frame.shape[0] != self.resolution[1]:
                            frame = cv2.resize(frame, self.resolution)
                        
                        # 写入帧
                        self.writer.write(frame)
                    
                    # 这里的 sleep 只是为了不让 CPU 跑满，dxcam.get_latest_frame() 是非阻塞的
                    elapsed = time.time() - loop_start
                    if elapsed < (frame_interval * 0.5):
                        time.sleep(0.001)
                        
                self.camera.stop()
                self.logger.info("DXCAM 录制循环已正常停止")
                return
            except Exception as e:
                self.logger.error(f"DXCAM 录制中出错: {e}，尝试切换到回退方案")
                try:
                    if self.camera: self.camera.stop()
                except:
                    pass

        # 回退方案: pyautogui 截图 (针对不兼容 DXGI 的系统)
        self.logger.info("正在使用回退截图方案进行录制...")
        while self.recording:
            try:
                loop_start = time.time()
                
                # 截取窗口画面
                x1, y1, x2, y2 = self.capture_region
                screenshot = pyautogui.screenshot(region=(x1, y1, x2-x1, y2-y1))
                
                # 转换为 OpenCV 格式
                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                
                # 调整分辨率
                if frame.shape[1] != self.resolution[0] or frame.shape[0] != self.resolution[1]:
                    frame = cv2.resize(frame, self.resolution)
                
                # 写入帧
                self.writer.write(frame)
                
                # 动态控制帧率，确保视频时长正确
                elapsed = time.time() - loop_start
                if elapsed < frame_interval:
                    time.sleep(frame_interval - elapsed)
                    
            except Exception as e:
                self.logger.error(f"回退录制帧时出错: {e}")
                time.sleep(0.1)
                continue
    
    def stop_recording(self):
        """停止录制"""
        if not self.recording:
            return
            
        self.recording = False
        
        # 等待录制线程结束
        if self.thread:
            self.thread.join(timeout=5)
        
        # 释放写入器
        if self.writer:
            self.writer.release()
            self.writer = None
        
        self.logger.info(f"录制已停止，视频已保存到: {self.output_path}")


def detect_win_screen(context, window):
    """
    检测是否为WIN结束界面
    通过检测屏幕上方的红色或青色"WIN"文字来判断
    
    Returns:
        (is_win_screen, win_type): 
            is_win_screen: 是否为WIN界面
            win_type: 'red'（对方赢）或'blue'（己方赢）或None
    """
    logger = context.shared.logger
    
    try:
        # 截取检测区域（屏幕上方30%）
        detection_region_rel = (0.2, 0.05, 0.6, 0.3)
        
        temp_screenshot_path = os.path.join(
            context.shared.base_temp_dir,
            f"win_detect_{int(time.time())}.png"
        )
        
        success = core_utils.take_screenshot(
            context,
            detection_region_rel,
            window,
            temp_screenshot_path
        )
        
        if not success or not os.path.exists(temp_screenshot_path):
            return (False, None)
        
        # 读取截图
        img = cv2.imread(temp_screenshot_path)
        if img is None:
            return (False, None)
        
        # 转换为RGB（OpenCV默认是BGR）
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # 检测红色WIN文字（对方赢）
        # RGB特征：R > 200, G < 80, B < 80
        red_mask = (img_rgb[:,:,0] > 200) & \
                   (img_rgb[:,:,1] < 80) & \
                   (img_rgb[:,:,2] < 80)
        red_ratio = np.sum(red_mask) / (img_rgb.shape[0] * img_rgb.shape[1])
        
        # 检测青色WIN文字（己方赢）
        # RGB特征：R < 100, G > 180, B > 180
        cyan_mask = (img_rgb[:,:,0] < 100) & \
                    (img_rgb[:,:,1] > 180) & \
                    (img_rgb[:,:,2] > 180)
        cyan_ratio = np.sum(cyan_mask) / (img_rgb.shape[0] * img_rgb.shape[1])
        
        # 清理临时文件
        try:
            os.remove(temp_screenshot_path)
        except:
            pass
        
        # 判断阈值（0.5%的像素）
        threshold = 0.005
        
        if red_ratio > threshold:
            logger.info(f"检测到红色WIN界面（对方赢），红色占比: {red_ratio:.4f}")
            return (True, 'red')
        elif cyan_ratio > threshold:
            logger.info(f"检测到青色WIN界面（己方赢），青色占比: {cyan_ratio:.4f}")
            return (True, 'blue')
        else:
            return (False, None)
        
    except Exception as e:
        logger.error(f"检测WIN界面时出错: {e}")
        return (False, None)


def click_play_button(context, window, button_index):
    """
    点击指定的播放按钮
    button_index: 0-4，对应5个播放按钮（Round 01-05）
    """
    logger = context.shared.logger
    
    # 播放按钮相对坐标（基于用户测量的 2379x1383 窗口坐标）
    play_button_coords_rel = [
        (0.6057, 0.5850),  # Round 01: (1441, 809) / (2379, 1383)
        (0.6057, 0.6247),  # Round 02: (1441, 864) / (2379, 1383)
        (0.6057, 0.6652),  # Round 03: (1441, 920) / (2379, 1383)
        (0.6057, 0.7064),  # Round 04: (1441, 977) / (2379, 1383)
        (0.6057, 0.7462),  # Round 05: (1441, 1032) / (2379, 1383)
    ]
    
    if button_index < 0 or button_index >= len(play_button_coords_rel):
        logger.error(f"无效的按钮索引: {button_index}")
        return False
    
    coord = play_button_coords_rel[button_index]
    logger.info(f"点击 Round {button_index + 1:02d} 播放按钮 (相对坐标: {coord[0]:.4f}, {coord[1]:.4f})")
    
    return core_utils.click_coordinates(context, coord, window)


def click_stats_button(context, window):
    """
    点击统计按钮（右下角）
    """
    logger = context.shared.logger
    
    # 统计按钮相对坐标: (1495, 1309) / (2379, 1383)
    stats_button_coord_rel = (0.6284, 0.9465)
    
    logger.info(f"点击统计按钮 (相对坐标: {stats_button_coord_rel[0]:.4f}, {stats_button_coord_rel[1]:.4f})")
    
    return core_utils.click_coordinates(context, stats_button_coord_rel, window)


def record_single_match(context, window, match_index, output_dir):
    """
    录制单场对局
    match_index: 对局索引（0-4）
    """
    logger = context.shared.logger
    mode_config = context.mode_config
    
    logger.info(f"===== 开始录制 Round {match_index + 1:02d} =====")
    
    # 检查停止信号
    if core_utils.check_stop_signal(context):
        logger.info("检测到停止信号，取消录制")
        return None
    
    # 生成输出文件名
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"match_{match_index + 1}_{timestamp}.mp4"
    output_path = os.path.join(output_dir, output_filename)
    
    # 获取视频参数
    # 降低默认 FPS 到 20，因为 pyautogui 截图速度有限，设置太高会导致视频快进
    fps = getattr(mode_config, 'm10_video_fps', 20)
    width = getattr(mode_config, 'm10_video_width', 1920)
    height = getattr(mode_config, 'm10_video_height', 1080)
    
    # 创建录制器
    recorder = VideoRecorder(context, output_path, fps=fps, resolution=(width, height))
    
    try:
        # 1. 点击播放按钮
        if not click_play_button(context, window, match_index):
            logger.error(f"点击 Round {match_index + 1:02d} 播放按钮失败")
            return None
        
        # 2. 等待视频开始播放
        logger.info("等待视频加载...")
        time.sleep(2.0)
        
        # 3. 开始录制
        hwnd = window._hWnd
        if not recorder.start_recording(hwnd):
            logger.error("启动录制失败")
            return None
        
        # 4. 循环检测WIN界面
        logger.info("开始监控WIN界面...")
        max_recording_time = 300  # 最长录制5分钟
        check_interval = 1.0  # 每秒检测一次
        elapsed_time = 0
        win_detected = False
        win_type = None
        
        while elapsed_time < max_recording_time:
            # 检查停止信号
            if core_utils.check_stop_signal(context):
                logger.info("检测到停止信号，停止录制")
                break
            
            # 检测WIN界面
            is_win, detected_type = detect_win_screen(context, window)
            if is_win:
                win_detected = True
                win_type = detected_type
                logger.info(f"检测到WIN界面！类型: {win_type}")
                break
            
            time.sleep(check_interval)
            elapsed_time += check_interval
        
        if elapsed_time >= max_recording_time:
            logger.warning(f"录制超时（{max_recording_time}秒），强制停止")
        
        # 5. 检测到WIN界面后的处理
        if win_detected:
            # 增加等待时间，确保动画播放完毕，统计按钮完全出现
            # 根据用户反馈，之前 0.5s 太快，2.0s 应该能确保按钮完全稳固
            logger.info("检测到WIN界面，等待 2.5 秒确保动画结束且统计按钮出现...")
            time.sleep(2.5)
            
            # 点击统计按钮
            click_stats_button(context, window)
            
            logger.info("已点击统计按钮，等待 2.0 秒确保数据完全显示...")
            time.sleep(2.0)
        
        # 6. 停止录制
        recorder.stop_recording()
        
        logger.info(f"Round {match_index + 1:02d} 录制完成: {output_path}")
        
        # 7. 退出到播放按钮界面（点击两次）
        logger.info("退出到播放按钮界面...")
        
        # 退出点击位置: (2005, 747) / (2379, 1383)
        exit_click_coord = (0.8428, 0.5401)
        
        # 第一次点击
        core_utils.click_coordinates(context, exit_click_coord, window)
        logger.info("第1次点击")
        time.sleep(1.0)  # 等待1秒
        
        # 第二次点击
        core_utils.click_coordinates(context, exit_click_coord, window)
        logger.info("第2次点击")
        time.sleep(0.5)  # 等待界面稳定
        
        logger.info("已返回播放按钮界面")
        
        return output_path
        
    except Exception as e:
        logger.error(f"录制 Round {match_index + 1:02d} 时出错: {e}")
        recorder.stop_recording()
        return None


def run(context):
    """模式10主函数"""
    logger = context.shared.logger
    nikke_window = context.shared.nikke_window
    mode_config = context.mode_config
    
    logger.info("===== 运行模式 10: 自动录屏 =====")
    
    if core_utils.check_stop_signal(context):
        logger.info("模式10：检测到停止信号，提前退出")
        return
    
    try:
        # 创建输出目录
        output_dir = core_utils.get_or_create_mode_output_subdir(context, 10, "recordings")
        if not output_dir:
            logger.error("模式10: 无法创建输出目录")
            return
        
        # 获取配置
        num_matches = getattr(mode_config, 'm10_num_matches', 5)  # 默认录制5场
        start_match = getattr(mode_config, 'm10_start_match', 0)  # 从第几场开始（0-4）
        
        logger.info(f"配置参数:")
        logger.info(f"  录制对局数量: {num_matches}")
        logger.info(f"  起始对局索引: {start_match}")
        logger.info(f"  视频帧率: {getattr(mode_config, 'm10_video_fps', 60)} fps")
        logger.info(f"  视频分辨率: {getattr(mode_config, 'm10_video_width', 1920)}x{getattr(mode_config, 'm10_video_height', 1080)}")
        
        # 确保窗口激活
        if not nikke_window:
            logger.error("模式10: 未找到游戏窗口")
            return
        
        # 逐场录制
        recorded_files = []
        for i in range(start_match, min(start_match + num_matches, 5)):
            if core_utils.check_stop_signal(context):
                logger.info("检测到停止信号，中止录制")
                break
            
            output_path = record_single_match(context, nikke_window, i, output_dir)
            if output_path:
                recorded_files.append(output_path)
            
            # 录制完一场后等待一下（已在record_single_match中退出到播放按钮界面）
            if i < start_match + num_matches - 1:
                logger.info("等待1秒后录制下一场...")
                time.sleep(1.0)  # 等待时间减少，因为已经退出到初始界面
        
        # 汇总结果
        logger.info(f"===== 模式10执行完毕 =====")
        logger.info(f"成功录制 {len(recorded_files)} 场对局:")
        for path in recorded_files:
            logger.info(f"  - {path}")
        
    except Exception as e:
        logger.exception(f"模式10执行期间发生错误: {e}")
        raise
    finally:
        logger.info("模式10执行完毕")
