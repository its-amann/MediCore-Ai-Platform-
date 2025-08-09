"""
WebSocket Message Router

Routes WebSocket messages to appropriate handlers and extensions.
"""

from typing import Dict, Any, List, Optional, Callable, TYPE_CHECKING
import logging
import asyncio
from dataclasses import dataclass
from enum import Enum

if TYPE_CHECKING:
    from ..manager import WebSocketManager

logger = logging.getLogger(__name__)


class RoutingStrategy(str, Enum):
    """Message routing strategies"""
    FIRST_MATCH = "first_match"      # Route to first matching handler
    ALL_MATCHING = "all_matching"    # Route to all matching handlers
    PRIORITY_ORDER = "priority_order" # Route based on handler priority
    ROUND_ROBIN = "round_robin"      # Round-robin among matching handlers


@dataclass
class RouteRule:
    """Message routing rule"""
    pattern: str                    # Message type pattern (supports wildcards)
    handler_name: str              # Target handler name
    priority: int = 100            # Rule priority (lower = higher priority)
    conditions: Dict[str, Any] = None  # Additional routing conditions
    enabled: bool = True           # Whether rule is enabled
    
    def __post_init__(self):
        if self.conditions is None:
            self.conditions = {}


class MessageRouter:
    """
    WebSocket Message Router
    
    Routes incoming WebSocket messages to appropriate handlers and extensions
    based on configurable rules and strategies.
    """
    
    def __init__(self, strategy: RoutingStrategy = RoutingStrategy.PRIORITY_ORDER):
        """
        Initialize the message router
        
        Args:
            strategy: Default routing strategy
        """
        self.strategy = strategy
        self.routes: List[RouteRule] = []
        self.custom_handlers: Dict[str, Callable] = {}
        self.middleware: List[Callable] = []
        
        # Routing statistics
        self.stats = {
            'messages_routed': 0,
            'routing_errors': 0,
            'unrouted_messages': 0,
            'handler_calls': {}
        }
        
        # Round-robin state for ROUND_ROBIN strategy
        self._round_robin_state: Dict[str, int] = {}
    
    def add_route(self, pattern: str, handler_name: str, priority: int = 100, **conditions):
        """
        Add a routing rule
        
        Args:
            pattern: Message type pattern (supports * wildcards)
            handler_name: Target handler name
            priority: Rule priority (lower = higher priority)
            **conditions: Additional routing conditions
        """
        rule = RouteRule(
            pattern=pattern,
            handler_name=handler_name,
            priority=priority,
            conditions=conditions
        )
        
        self.routes.append(rule)
        self.routes.sort(key=lambda r: r.priority)  # Keep sorted by priority
        
        logger.info(f"Added route: {pattern} -> {handler_name} (priority: {priority})")
    
    def remove_route(self, pattern: str, handler_name: str):
        """Remove a routing rule"""
        self.routes = [
            rule for rule in self.routes 
            if not (rule.pattern == pattern and rule.handler_name == handler_name)
        ]
        logger.info(f"Removed route: {pattern} -> {handler_name}")
    
    def add_custom_handler(self, name: str, handler: Callable):
        """
        Add a custom message handler
        
        Args:
            name: Handler name
            handler: Handler function (async callable)
        """
        self.custom_handlers[name] = handler
        logger.info(f"Added custom handler: {name}")
    
    def add_middleware(self, middleware: Callable):
        """
        Add middleware for message processing
        
        Args:
            middleware: Middleware function (async callable)
        """
        self.middleware.append(middleware)
        logger.info(f"Added middleware: {middleware.__name__}")
    
    async def route_message(self, connection_id: str, message: Dict[str, Any], manager: 'WebSocketManager') -> bool:
        """
        Route a message to appropriate handlers
        
        Args:
            connection_id: Connection ID that sent the message
            message: Message payload
            manager: WebSocket manager instance
            
        Returns:
            bool: True if message was routed and handled
        """
        try:
            self.stats['messages_routed'] += 1
            
            # Apply middleware
            for middleware in self.middleware:
                try:
                    message = await middleware(connection_id, message, manager)
                    if message is None:
                        # Middleware consumed the message
                        return True
                except Exception as e:
                    logger.error(f"Middleware error: {e}")
                    continue
            
            message_type = message.get("type", "")
            if not message_type:
                logger.warning(f"Message without type from {connection_id}")
                return False
            
            # Find matching routes
            matching_routes = self._find_matching_routes(message_type, message)
            
            if not matching_routes:
                self.stats['unrouted_messages'] += 1
                logger.debug(f"No routes found for message type: {message_type}")
                return False
            
            # Route based on strategy
            return await self._execute_routing_strategy(
                matching_routes, connection_id, message, manager
            )
        
        except Exception as e:
            self.stats['routing_errors'] += 1
            logger.error(f"Error routing message: {e}")
            return False
    
    def _find_matching_routes(self, message_type: str, message: Dict[str, Any]) -> List[RouteRule]:
        """Find routes that match the message"""
        matching_routes = []
        
        for route in self.routes:
            if not route.enabled:
                continue
            
            # Check pattern match
            if self._pattern_matches(route.pattern, message_type):
                # Check additional conditions
                if self._check_conditions(route.conditions, message):
                    matching_routes.append(route)
        
        return matching_routes
    
    def _pattern_matches(self, pattern: str, message_type: str) -> bool:
        """Check if pattern matches message type"""
        if pattern == "*":
            return True
        
        if "*" not in pattern:
            return pattern == message_type
        
        # Handle wildcard patterns
        import fnmatch
        return fnmatch.fnmatch(message_type, pattern)
    
    def _check_conditions(self, conditions: Dict[str, Any], message: Dict[str, Any]) -> bool:
        """Check if message meets routing conditions"""
        if not conditions:
            return True
        
        for key, expected_value in conditions.items():
            if key not in message:
                return False
            
            actual_value = message[key]
            
            # Handle different condition types
            if isinstance(expected_value, list):
                if actual_value not in expected_value:
                    return False
            elif isinstance(expected_value, dict):
                # Support for complex conditions like {"gt": 10}
                for op, value in expected_value.items():
                    if op == "gt" and actual_value <= value:
                        return False
                    elif op == "lt" and actual_value >= value:
                        return False
                    elif op == "eq" and actual_value != value:
                        return False
                    # Add more operators as needed
            else:
                if actual_value != expected_value:
                    return False
        
        return True
    
    async def _execute_routing_strategy(
        self, 
        routes: List[RouteRule], 
        connection_id: str, 
        message: Dict[str, Any], 
        manager: 'WebSocketManager'
    ) -> bool:
        """Execute routing based on configured strategy"""
        
        if self.strategy == RoutingStrategy.FIRST_MATCH:
            return await self._route_first_match(routes, connection_id, message, manager)
        
        elif self.strategy == RoutingStrategy.ALL_MATCHING:
            return await self._route_all_matching(routes, connection_id, message, manager)
        
        elif self.strategy == RoutingStrategy.PRIORITY_ORDER:
            return await self._route_priority_order(routes, connection_id, message, manager)
        
        elif self.strategy == RoutingStrategy.ROUND_ROBIN:
            return await self._route_round_robin(routes, connection_id, message, manager)
        
        else:
            logger.error(f"Unknown routing strategy: {self.strategy}")
            return False
    
    async def _route_first_match(
        self, routes: List[RouteRule], connection_id: str, message: Dict[str, Any], manager: 'WebSocketManager'
    ) -> bool:
        """Route to first matching handler"""
        if routes:
            return await self._call_handler(routes[0], connection_id, message, manager)
        return False
    
    async def _route_all_matching(
        self, routes: List[RouteRule], connection_id: str, message: Dict[str, Any], manager: 'WebSocketManager'
    ) -> bool:
        """Route to all matching handlers"""
        success = False
        for route in routes:
            if await self._call_handler(route, connection_id, message, manager):
                success = True
        return success
    
    async def _route_priority_order(
        self, routes: List[RouteRule], connection_id: str, message: Dict[str, Any], manager: 'WebSocketManager'
    ) -> bool:
        """Route to highest priority handler"""
        # Routes are already sorted by priority
        if routes:
            return await self._call_handler(routes[0], connection_id, message, manager)
        return False
    
    async def _route_round_robin(
        self, routes: List[RouteRule], connection_id: str, message: Dict[str, Any], manager: 'WebSocketManager'
    ) -> bool:
        """Route using round-robin among matching handlers"""
        if not routes:
            return False
        
        message_type = message.get("type", "")
        
        # Get or initialize round-robin index
        if message_type not in self._round_robin_state:
            self._round_robin_state[message_type] = 0
        
        # Select handler based on round-robin
        index = self._round_robin_state[message_type] % len(routes)
        selected_route = routes[index]
        
        # Update round-robin state
        self._round_robin_state[message_type] = (index + 1) % len(routes)
        
        return await self._call_handler(selected_route, connection_id, message, manager)
    
    async def _call_handler(
        self, route: RouteRule, connection_id: str, message: Dict[str, Any], manager: 'WebSocketManager'
    ) -> bool:
        """Call a specific handler"""
        handler_name = route.handler_name
        
        try:
            # Update statistics
            if handler_name not in self.stats['handler_calls']:
                self.stats['handler_calls'][handler_name] = 0
            self.stats['handler_calls'][handler_name] += 1
            
            # Try custom handlers first
            if handler_name in self.custom_handlers:
                handler = self.custom_handlers[handler_name]
                result = await handler(connection_id, message, manager)
                return bool(result)
            
            # Try extension handlers
            extension = manager.get_extension(handler_name)
            if extension:
                return await extension.on_message(connection_id, message)
            
            # Try registered handlers in manager
            registry = manager._registry
            handler = registry.get_handler(handler_name)
            if handler:
                return await handler.handle(connection_id, message, manager)
            
            logger.warning(f"Handler not found: {handler_name}")
            return False
        
        except Exception as e:
            logger.error(f"Error calling handler {handler_name}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        return self.stats.copy()
    
    def get_routes(self) -> List[Dict[str, Any]]:
        """Get all routing rules"""
        return [
            {
                'pattern': route.pattern,
                'handler_name': route.handler_name,
                'priority': route.priority,
                'conditions': route.conditions,
                'enabled': route.enabled
            }
            for route in self.routes
        ]
    
    def clear_stats(self):
        """Clear routing statistics"""
        self.stats = {
            'messages_routed': 0,
            'routing_errors': 0,
            'unrouted_messages': 0,
            'handler_calls': {}
        }
        logger.info("Routing statistics cleared")
    
    def enable_route(self, pattern: str, handler_name: str):
        """Enable a specific route"""
        for route in self.routes:
            if route.pattern == pattern and route.handler_name == handler_name:
                route.enabled = True
                logger.info(f"Enabled route: {pattern} -> {handler_name}")
                break
    
    def disable_route(self, pattern: str, handler_name: str):
        """Disable a specific route"""
        for route in self.routes:
            if route.pattern == pattern and route.handler_name == handler_name:
                route.enabled = False
                logger.info(f"Disabled route: {pattern} -> {handler_name}")
                break