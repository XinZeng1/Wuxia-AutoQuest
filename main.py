"""
游戏自动刷图主程序 - 新版本（怪物优先策略）
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
from src.map_navigation.exploration_navigator import ExplorationNavigator
from src.monster_detection.monster_detector import MonsterDetector
from src.exploration_tracking.exploration_tracker import ExplorationTracker


class AutoFarming:
    """自动刷图主类 - 怪物优先策略"""

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
        self.exploration_navigator = ExplorationNavigator(
            screenshot=self.screenshot,
            navigator=self.navigator
        )

        # 初始化状态机
        self.state_machine = StateMachine()
        self._setup_state_machine()

        # 探索统计
        self.no_monster_count = 0  # 连续无怪物计数
        self.max_no_monster_before_systematic = 3  # 连续N次无怪物后启用系统扫描

        self.logger.info("自动刷图系统初始化完成（怪物优先策略）")

    def _setup_state_machine(self):
        """设置状态机"""
        self.state_machine.set_state_handler(State.IDLE, self._handle_idle)
        self.state_machine.set_state_handler(State.SCANNING_MONSTERS, self._handle_scanning_monsters)
        self.state_machine.set_state_handler(State.MOVING_TO_MONSTER, self._handle_moving_to_monster)
        self.state_machine.set_state_handler(State.WAITING_FOR_COMBAT, self._handle_waiting_for_combat)
        self.state_machine.set_state_handler(State.COMBAT, self._handle_combat)
        self.state_machine.set_state_handler(State.EXPLORING, self._handle_exploring)
        self.state_machine.set_state_handler(State.COMPLETED, self._handle_completed)

        # 状态转换
        self.state_machine.add_transition(State.IDLE, State.SCANNING_MONSTERS)
        self.state_machine.add_transition(State.SCANNING_MONSTERS, State.MOVING_TO_MONSTER)
        self.state_machine.add_transition(State.SCANNING_MONSTERS, State.EXPLORING)
        self.state_machine.add_transition(State.SCANNING_MONSTERS, State.COMPLETED)
        self.state_machine.add_transition(State.MOVING_TO_MONSTER, State.WAITING_FOR_COMBAT)
        self.state_machine.add_transition(State.WAITING_FOR_COMBAT, State.COMBAT)
        self.state_machine.add_transition(State.WAITING_FOR_COMBAT, State.SCANNING_MONSTERS)
        self.state_machine.add_transition(State.COMBAT, State.SCANNING_MONSTERS)
        self.state_machine.add_transition(State.EXPLORING, State.SCANNING_MONSTERS)
        self.state_machine.add_transition(State.COMPLETED, State.STOPPED)

    def _handle_idle(self):
        """处理空闲状态"""
        self.logger.info("系统空闲，开始扫描怪物")
        self.state_machine.transition_to(State.SCANNING_MONSTERS)

    def _handle_scanning_monsters(self):
        """扫描怪物状态"""
        try:
            # 跳过探索度检测（太慢）
            # current_exploration = self.exploration_tracker.get_current_exploration()
            # if current_exploration is not None:
            #     self.logger.info(f"当前探索度: {current_exploration}%")
            #
            #     # 检查是否完成
            #     if self.exploration_tracker.is_exploration_complete():
            #         self.logger.info("探索度已达到100%，完成！")
            #         self.state_machine.transition_to(State.COMPLETED)
            #         return

            # 检测是否在战斗中（可能是之前的战斗还未结束）
            if self.combat_detector.is_in_combat():
                self.logger.info("检测到战斗状态，进入战斗")
                self.state_machine.transition_to(State.COMBAT)
                return

            # 扫描怪物
            monsters = self.monster_detector.detect_monsters()

            if monsters:
                self.logger.info(f"检测到 {len(monsters)} 个怪物")
                self.no_monster_count = 0  # 重置计数
                self.state_machine.transition_to(State.MOVING_TO_MONSTER)
            else:
                self.logger.debug("未检测到怪物，进入探索模式")
                self.no_monster_count += 1
                self.state_machine.transition_to(State.EXPLORING)

            time.sleep(0.5)  # 短暂延迟

        except Exception as e:
            self.logger.error(f"扫描怪物时出错: {e}", exc_info=True)
            time.sleep(1)

    def _handle_moving_to_monster(self):
        """移动到怪物状态"""
        try:
            # 选择最近的怪物
            current_pos = self.navigator.get_current_position()

            if current_pos is None:
                self.logger.warning("无法检测角色位置，将选择第一个检测到的怪物")

            monster = self.monster_detector.select_nearest_monster(current_pos)

            if monster:
                # 移动到怪物位置
                self.logger.info(f"移动到怪物位置: ({monster[0]}, {monster[1]})")
                self.navigator.move_to_monster(monster)
                self.state_machine.transition_to(State.WAITING_FOR_COMBAT)
            else:
                self.logger.warning("未找到怪物，返回扫描")
                self.state_machine.transition_to(State.SCANNING_MONSTERS)

        except Exception as e:
            self.logger.error(f"移动到怪物时出错: {e}", exc_info=True)
            self.state_machine.transition_to(State.SCANNING_MONSTERS)

    def _handle_waiting_for_combat(self):
        """等待战斗状态"""
        # 获取配置的等待时间
        post_click_wait = self.config.get('game.post_click_wait', 1.5)
        self.logger.info(f"等待 {post_click_wait} 秒让角色走向怪物...")
        time.sleep(post_click_wait)

        # 检测战斗状态（重试机制）
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

        self.logger.warning(f"经过{max_retries}次检测仍未进入战斗，返回扫描")
        self.state_machine.transition_to(State.SCANNING_MONSTERS)

    def _handle_combat(self):
        """战斗状态"""
        success = self.combat_detector.wait_for_combat_end()
        if not success:
            self.logger.error("战斗超时")
            # 不停止，继续扫描
            self.state_machine.transition_to(State.SCANNING_MONSTERS)
            return

        self.logger.info("战斗结束，继续扫描怪物")
        time.sleep(1.0)  # 战斗结束后短暂等待
        self.state_machine.transition_to(State.SCANNING_MONSTERS)

    def _handle_exploring(self):
        """探索新区域状态"""
        try:
            # 检查是否卡死
            if self.exploration_navigator.is_stuck():
                self.logger.warning("检测到卡死，执行随机逃逸")
                self.exploration_navigator.escape()
                time.sleep(1.0)
                self.state_machine.transition_to(State.SCANNING_MONSTERS)
                return

            # 策略1：尝试使用小地图引导
            if self.no_monster_count < self.max_no_monster_before_systematic:
                self.logger.debug("尝试使用小地图引导探索")
                if self.exploration_navigator.explore_to_unexplored():
                    time.sleep(1.5)  # 移动后等待
                    self.state_machine.transition_to(State.SCANNING_MONSTERS)
                    return

            # 策略2：小地图引导失败，使用系统扫描
            self.logger.debug("使用系统扫描探索")
            self.exploration_navigator.explore_systematic()
            time.sleep(1.5)  # 移动后等待
            self.state_machine.transition_to(State.SCANNING_MONSTERS)

        except Exception as e:
            self.logger.error(f"探索时出错: {e}", exc_info=True)
            time.sleep(1)
            self.state_machine.transition_to(State.SCANNING_MONSTERS)

    def _handle_completed(self):
        """完成状态"""
        self.logger.info("=" * 50)
        self.logger.info("探索完成！")
        self.logger.info("=" * 50)
        time.sleep(1)
        self.state_machine.transition_to(State.STOPPED)

    def start(self):
        """启动自动刷图"""
        self.logger.info("启动自动刷图系统（怪物优先策略）")
        self.state_machine.transition_to(State.SCANNING_MONSTERS)

        # 检查必要的模板文件
        monster_template = self.monster_detector.monster_template
        if monster_template:
            template_path = Path(__file__).parent / "templates" / monster_template
            if not template_path.exists():
                self.logger.warning(f"怪物模板文件不存在: {template_path}")
                self.logger.warning("程序将继续运行，但可能无法检测怪物")

        try:
            loop_count = 0
            while not self.state_machine.is_stopped() and not self.state_machine.is_completed():
                current_state = self.state_machine.get_state()

                # 每10次循环输出一次状态
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
