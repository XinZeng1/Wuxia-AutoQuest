"""
游戏自动刷图主程序
"""
import sys
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.config import get_config
from src.core.logger import setup_logger, get_logger
from src.core.state_machine import StateMachine, State
from src.core.combat_state import CombatStateDetector
from src.ui_interaction.screenshot import Screenshot
from src.map_navigation.map_navigator import MapNavigator
from src.map_navigation.boundary_cruise import BoundaryCruiseDriver
from src.monster_detection.monster_detector import MonsterDetector
from src.exploration_tracking.exploration_tracker import ExplorationTracker


class AutoFarming:
    """自动刷图主类"""
    
    def __init__(self):
        """初始化自动刷图系统"""
        # 加载配置
        self.config = get_config()
        
        # 设置日志
        log_config = self.config.get('logging', {})
        setup_logger(
            level=log_config.get('level', 'INFO'),
            log_file=log_config.get('file'),
            console=log_config.get('console', True)
        )
        self.logger = get_logger(__name__)
        
        # 初始化各个模块
        self.screenshot = Screenshot()
        self.navigator = MapNavigator()
        self.monster_detector = MonsterDetector()
        self.exploration_tracker = ExplorationTracker()
        self.combat_detector = CombatStateDetector()
        self.cruise_driver = BoundaryCruiseDriver(screenshot=self.screenshot, navigator=self.navigator)
        
        # 初始化状态机
        self.state_machine = StateMachine()
        self._setup_state_machine()
        
        self.logger.info("自动刷图系统初始化完成")
    
    def _setup_state_machine(self):
        """设置状态机：A 边界巡航 / B 精确打击 / C 原路回溯"""
        self.state_machine.set_state_handler(State.IDLE, self._handle_idle)
        self.state_machine.set_state_handler(State.BOUNDARY_CRUISE, self._handle_boundary_cruise)
        self.state_machine.set_state_handler(State.MOVING_TO_MONSTER, self._handle_moving_to_monster)
        self.state_machine.set_state_handler(State.WAITING_FOR_COMBAT, self._handle_waiting_for_combat)
        self.state_machine.set_state_handler(State.COMBAT, self._handle_combat)
        self.state_machine.set_state_handler(State.BACKTRACKING, self._handle_backtracking)
        self.state_machine.set_state_handler(State.PAUSED, self._handle_paused)
        
        self.state_machine.add_transition(State.IDLE, State.BOUNDARY_CRUISE)
        self.state_machine.add_transition(State.BOUNDARY_CRUISE, State.MOVING_TO_MONSTER)
        self.state_machine.add_transition(State.BOUNDARY_CRUISE, State.PAUSED)
        self.state_machine.add_transition(State.MOVING_TO_MONSTER, State.WAITING_FOR_COMBAT)
        self.state_machine.add_transition(State.WAITING_FOR_COMBAT, State.COMBAT)
        self.state_machine.add_transition(State.WAITING_FOR_COMBAT, State.BOUNDARY_CRUISE)
        self.state_machine.add_transition(State.COMBAT, State.BOUNDARY_CRUISE)
        self.state_machine.add_transition(State.COMBAT, State.MOVING_TO_MONSTER)
        self.state_machine.add_transition(State.COMBAT, State.BACKTRACKING)
        self.state_machine.add_transition(State.BACKTRACKING, State.BOUNDARY_CRUISE)
        self.state_machine.add_transition(State.PAUSED, State.BOUNDARY_CRUISE)
    
    def _handle_idle(self):
        """处理空闲状态"""
        self.logger.info("系统空闲，开始边界巡航")
        self.state_machine.transition_to(State.BOUNDARY_CRUISE)
    
    def _handle_boundary_cruise(self):
        """A: 边界巡航。发现怪物则压栈并切到精确打击。"""
        try:
            cruise_interval = float((self.config.get('minimap') or {}).get('cruise_interval_sec', 1.2))
            current = self.exploration_tracker.get_current_exploration()
            if current is not None:
                self.logger.info(f"当前探索度: {current}%")
            else:
                if self.combat_detector.is_in_combat():
                    self.logger.info("检测到战斗状态，进入战斗")
                    self.state_machine.transition_to(State.COMBAT)
                    return
            if self.exploration_tracker.is_exploration_complete():
                self.logger.info("探索度已达到目标，停止")
                self.state_machine.transition_to(State.STOPPED)
                return
            
            try:
                monsters = self.monster_detector.detect_monsters()
                if monsters:
                    pos = self.cruise_driver.last_move_target or self.cruise_driver.get_center_position()
                    self.cruise_driver.push(pos)
                    self.logger.info(f"检测到 {len(monsters)} 个怪物，压栈后进入精确打击")
                    self.state_machine.transition_to(State.MOVING_TO_MONSTER)
                    return
            except Exception as e:
                self.logger.debug("怪物检测跳过: %s", e)
            
            if self.cruise_driver.is_stuck_cruise():
                self.cruise_driver.trigger_escape()
                time.sleep(cruise_interval)
                return

            full = self.screenshot.capture_full_window()
            if self.cruise_driver.cruise_tick(full):
                time.sleep(cruise_interval)
            else:
                time.sleep(cruise_interval)
        except Exception as e:
            self.logger.error("边界巡航出错: %s", e, exc_info=True)
            time.sleep(1)
    
    def _handle_moving_to_monster(self):
        """处理移动到怪物状态"""
        try:
            # 选择最近的怪物
            current_pos = self.navigator.get_current_position()
            
            # 如果无法检测角色位置，仍然可以移动（选择第一个或置信度最高的怪物）
            if current_pos is None:
                self.logger.warning("无法检测角色位置，将选择第一个检测到的怪物")
            
            monster = self.monster_detector.select_nearest_monster(current_pos)
            
            if monster:
                # 移动到怪物位置
                self.logger.info(f"准备移动到怪物位置: ({monster[0]}, {monster[1]})")
                self.navigator.move_to_monster(monster)
                self.state_machine.transition_to(State.WAITING_FOR_COMBAT)
            else:
                self.logger.warning("未找到怪物，返回边界巡航")
                self.state_machine.transition_to(State.BOUNDARY_CRUISE)
        except Exception as e:
            self.logger.error(f"移动到怪物时出错: {e}", exc_info=True)
            self.state_machine.transition_to(State.BOUNDARY_CRUISE)
    
    def _handle_waiting_for_combat(self):
        """处理等待战斗状态"""
        # 获取配置的等待时间（让角色走向怪物）
        post_click_wait = self.config.get('game.post_click_wait', 1.5)
        self.logger.info(f"等待 {post_click_wait} 秒让角色走向怪物...")
        time.sleep(post_click_wait)
        
        # 增加重试机制，最多检测3次，提高战斗状态检测的准确性
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            if self.combat_detector.is_in_combat():
                self.logger.info(f"进入战斗状态（第{attempt + 1}次检测成功）")
                self.state_machine.transition_to(State.COMBAT)
                return
            
            if attempt < max_retries - 1:
                self.logger.debug(f"未检测到战斗状态，等待{retry_delay}秒后进行第{attempt + 2}次检测...")
                time.sleep(retry_delay)
        
        self.logger.warning(f"经过{max_retries}次检测仍未进入战斗，返回边界巡航")
        self.state_machine.transition_to(State.BOUNDARY_CRUISE)
    
    def _handle_combat(self):
        """B: 精确打击-战斗中。结束后无怪则回溯，有怪则压栈继续打。"""
        success = self.combat_detector.wait_for_combat_end()
        if not success:
            self.logger.error("战斗超时，停止")
            self.state_machine.transition_to(State.STOPPED)
            return
        self.logger.info("战斗结束")
        try:
            monsters = self.monster_detector.detect_monsters()
            if monsters:
                pos = self.navigator.get_current_position() or self.cruise_driver.get_center_position()
                self.cruise_driver.push(pos)
                self.logger.info("视野内仍有怪物，压栈后继续打击")
                self.state_machine.transition_to(State.MOVING_TO_MONSTER)
            else:
                self.logger.info("视野内无怪物，进入原路回溯")
                self.state_machine.transition_to(State.BACKTRACKING)
        except Exception as e:
            self.logger.debug("战后怪物检测异常: %s", e)
            self.state_machine.transition_to(State.BACKTRACKING)
    
    def _handle_backtracking(self):
        """C: 原路回溯。栈空且归位后回边界巡航；卡死则逃逸清栈再巡航。"""
        try:
            res = self.cruise_driver.backtrack_tick()
            if res == "stuck":
                self.cruise_driver.trigger_escape()
                self.state_machine.transition_to(State.BOUNDARY_CRUISE)
                return
            if res == "done":
                self.logger.info("回溯完成，恢复边界巡航")
                self.state_machine.transition_to(State.BOUNDARY_CRUISE)
                return
            time.sleep(0.3)
        except Exception as e:
            self.logger.error("回溯出错: %s", e, exc_info=True)
            self.cruise_driver.clear_stack()
            self.state_machine.transition_to(State.BOUNDARY_CRUISE)
    
    def _handle_paused(self):
        """处理暂停状态"""
        time.sleep(0.5)
    
    def start(self):
        """启动自动刷图"""
        self.logger.info("启动自动刷图系统（边界巡航+回溯）")
        self.state_machine.transition_to(State.BOUNDARY_CRUISE)
        
        # 检查必要的模板文件
        monster_template = self.monster_detector.monster_template
        template_path = Path(__file__).parent / "templates" / monster_template
        if not template_path.exists():
            self.logger.warning(f"怪物模板文件不存在: {template_path}")
            self.logger.warning("程序将继续运行，但无法检测怪物")
        
        try:
            loop_count = 0
            while not self.state_machine.is_stopped():
                if self.state_machine.is_paused():
                    self._handle_paused()
                else:
                    current_state = self.state_machine.get_state()
                    # 每10次循环输出一次状态（避免日志过多）
                    if loop_count % 10 == 0:
                        self.logger.debug(f"当前状态: {current_state.value}, 循环次数: {loop_count}")
                    self.state_machine.update()
                    loop_count += 1
                
                time.sleep(0.1)  # 主循环延迟
        except KeyboardInterrupt:
            self.logger.info("收到中断信号，停止系统")
            self.stop()
        except Exception as e:
            self.logger.error(f"运行出错: {e}", exc_info=True)
            self.stop()
    
    def stop(self):
        """停止自动刷图"""
        self.logger.info("停止自动刷图系统")
        self.state_machine.transition_to(State.STOPPED)
    
    def pause(self):
        """暂停自动刷图"""
        self.logger.info("暂停自动刷图系统")
        self.state_machine.transition_to(State.PAUSED)
    
    def resume(self):
        """恢复自动刷图"""
        self.logger.info("恢复自动刷图系统")
        self.state_machine.transition_to(State.BOUNDARY_CRUISE)


def main():
    """主函数"""
    try:
        farming = AutoFarming()
        farming.start()
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"程序启动失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
