"""
Unit tests for C code parser.
"""

import unittest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.parser import CCodeParser
from models.event_action import EventAction

class TestCCodeParser(unittest.TestCase):
    """Test C code parser functionality."""
    
    def test_parse_simple_action(self):
        """Test parsing a simple EventAction."""
        c_code = "EventAction input1_singlePress = { on, off, 5000, 100, 64, 0, 0, 1 };"
        actions = CCodeParser.parse_c_code(c_code)
        
        self.assertIn("input1_singlePress", actions)
        action = actions["input1_singlePress"]
        
        self.assertEqual(action.name, "input1_singlePress")
        self.assertEqual(action.action, "on")
        self.assertEqual(action.delay_action, "off")
        self.assertEqual(action.delay, 5000)
        self.assertEqual(action.brightness, 100)
        self.assertEqual(action.node, 64)
        self.assertEqual(action.output, 0)
        self.assertEqual(action.extra_action_index, 1)
    
    def test_parse_multiple_actions(self):
        """Test parsing multiple EventActions."""
        c_code = """
        EventAction input1_singlePress = { on, off, 5000, 100, 64, 0, 0, 1 };
        EventAction input1_doublePress = { toggle, nop, 0, 100, 64, 1, 0, 0 };
        EventAction extraAction1 = { off, on, 3000, 80, 65, 2, 0, 0 };
        """
        actions = CCodeParser.parse_c_code(c_code)
        
        self.assertEqual(len(actions), 3)
        self.assertIn("input1_singlePress", actions)
        self.assertIn("input1_doublePress", actions)
        self.assertIn("extraAction1", actions)
    
    def test_parse_with_comments(self):
        """Test parsing with C comments."""
        c_code = """
        // This is a comment
        EventAction input1_singlePress = { on, off, 5000, 100, 64, 0, 0, 1 };
        /* Multi-line
           comment */
        EventAction input2_longPress = { toggle, nop, 0, 100, 64, 2, 0, 0 };
        """
        actions = CCodeParser.parse_c_code(c_code)
        
        self.assertEqual(len(actions), 2)
    
    def test_validate_valid_code(self):
        """Test validation of valid C code."""
        c_code = "EventAction input1_singlePress = { on, off, 5000, 100, 64, 0, 0, 1 };"
        errors = CCodeParser.validate_c_code(c_code)
        
        self.assertEqual(len(errors), 0)
    
    def test_validate_missing_semicolon(self):
        """Test validation catches missing semicolon."""
        c_code = "EventAction input1_singlePress = { on, off, 5000, 100, 64, 0, 0, 1 }"
        errors = CCodeParser.validate_c_code(c_code)
        
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("semicolon" in err.lower() for err in errors))
    
    def test_validate_wrong_field_count(self):
        """Test validation catches wrong number of fields."""
        c_code = "EventAction input1_singlePress = { on, off, 5000, 100, 64 };"
        errors = CCodeParser.validate_c_code(c_code)
        
        self.assertGreater(len(errors), 0)
    
    def test_parse_to_device(self):
        """Test parsing C code to Device object."""
        c_code = """
        EventAction input1_singlePress = { on, off, 5000, 100, 64, 0, 0, 1 };
        EventAction input2_doublePress = { toggle, nop, 0, 100, 64, 1, 0, 0 };
        EventAction extraAction1 = { off, on, 3000, 80, 65, 2, 0, 0 };
        """
        device = CCodeParser.parse_to_device(c_code, "Test Device")
        
        self.assertEqual(device.name, "Test Device")
        self.assertGreaterEqual(device.num_inputs, 2)
        self.assertGreaterEqual(device.num_extra_actions, 1)
        
        # Check that actions were populated
        self.assertEqual(device.input_actions["input1_singlePress"].action, "on")
        self.assertEqual(device.extra_actions["extraAction1"].action, "off")

class TestEventAction(unittest.TestCase):
    """Test EventAction model."""
    
    def test_to_c_code(self):
        """Test EventAction to C code conversion."""
        action = EventAction(
            name="input1_singlePress",
            action="on",
            delay_action="off",
            delay=5000,
            brightness=100,
            node=64,
            output=0,
            extra_action_index=1
        )
        
        c_code = action.to_c_code()
        expected = "EventAction input1_singlePress = { on, off, 5000, 100, 64, 0, 0, 1 };"
        
        self.assertEqual(c_code, expected)
    
    def test_resolve_composite_action(self):
        """Test resolving composite actions."""
        action = EventAction("test", action="ondelayoff")
        resolved_action, resolved_delay = action.resolve_composite_action()
        
        self.assertEqual(resolved_action, "on")
        self.assertEqual(resolved_delay, "off")
        
        action2 = EventAction("test2", action="offdelayon")
        resolved_action2, resolved_delay2 = action2.resolve_composite_action()
        
        self.assertEqual(resolved_action2, "off")
        self.assertEqual(resolved_delay2, "on")
    
    def test_is_empty(self):
        """Test empty action detection."""
        empty_action = EventAction("test")
        self.assertTrue(empty_action.is_empty())
        
        non_empty = EventAction("test", action="on")
        self.assertFalse(non_empty.is_empty())
    
    def test_validate(self):
        """Test action validation."""
        # Valid action
        valid = EventAction("test", action="on", brightness=50)
        errors = valid.validate()
        self.assertEqual(len(errors), 0)
        
        # Invalid action
        invalid = EventAction("test", action="invalid_action")
        errors = invalid.validate()
        self.assertGreater(len(errors), 0)
        
        # Invalid brightness
        invalid_bright = EventAction("test", brightness=150)
        errors = invalid_bright.validate()
        self.assertGreater(len(errors), 0)

if __name__ == '__main__':
    unittest.main()
