"""
状态机模块
"""
from enum import Enum
from typing import Optional, Callable
from src.core.logger import get_logger

logger = get_logger(__name__)


class State(Enum):
    """状态枚举"""
    IDLE = "idle"  # 空闲
    SCANNING_MONSTERS = "scanning_monsters"  # 扫描怪物
    MOVING_TO_MONSTER = "moving_to_monster"  # 移动到怪物
    WAITING_FOR_COMBAT = "waiting_for_combat"  # 等待战斗
    COMBAT = "combat"  # 战斗中
    EXPLORING = "exploring"  # 探索新区域
    COMPLETED = "completed"  # 探索完成
    STOPPED = "stopped"  # 停止


class StateMachine:
    """状态机类"""
    
    def __init__(self):
        """初始化状态机"""
        self.current_state = State.IDLE
        self.state_handlers: dict = {}
        self.transitions: dict = {}
    
    def set_state_handler(self, state: State, handler: Callable):
        """
        设置状态处理函数
        
        Args:
            state: 状态
            handler: 处理函数
        """
        self.state_handlers[state] = handler
        logger.debug(f"设置状态处理函数: {state.value}")
    
    def add_transition(self, from_state: State, to_state: State, condition: Optional[Callable] = None):
        """
        添加状态转换
        
        Args:
            from_state: 源状态
            to_state: 目标状态
            condition: 转换条件函数（可选）
        """
        if from_state not in self.transitions:
            self.transitions[from_state] = []
        
        self.transitions[from_state].append({
            'to': to_state,
            'condition': condition
        })
        logger.debug(f"添加状态转换: {from_state.value} -> {to_state.value}")
    
    def transition_to(self, new_state: State):
        """
        转换到新状态
        
        Args:
            new_state: 新状态
        """
        old_state = self.current_state
        self.current_state = new_state
        logger.info(f"状态转换: {old_state.value} -> {new_state.value}")
    
    def can_transition_to(self, to_state: State) -> bool:
        """
        检查是否可以转换到目标状态
        
        Args:
            to_state: 目标状态
        
        Returns:
            是否可以转换
        """
        if self.current_state not in self.transitions:
            return False
        
        for transition in self.transitions[self.current_state]:
            if transition['to'] == to_state:
                if transition['condition'] is None:
                    return True
                elif transition['condition']():
                    return True
        
        return False
    
    def update(self):
        """更新状态机（执行当前状态的处理函数）"""
        if self.current_state in self.state_handlers:
            handler = self.state_handlers[self.current_state]
            handler()
    
    def get_state(self) -> State:
        """获取当前状态"""
        return self.current_state
    
    def is_stopped(self) -> bool:
        """检查是否已停止"""
        return self.current_state == State.STOPPED

    def is_completed(self) -> bool:
        """检查是否已完成"""
        return self.current_state == State.COMPLETED
