"""
Testes para o módulo calculadora.
"""

import unittest
from calculator import add, subtract, multiply, divide, Calculator


class TestBasicOperations(unittest.TestCase):
    """Testes para operações básicas."""
    
    def test_add(self):
        """Testa adição."""
        self.assertEqual(add(2, 3), 5)
        self.assertEqual(add(-1, 1), 0)
    
    def test_subtract(self):
        """Testa subtração."""
        self.assertEqual(subtract(5, 3), 2)
        self.assertEqual(subtract(0, 5), -5)
    
    def test_multiply(self):
        """Testa multiplicação."""
        self.assertEqual(multiply(3, 4), 12)
        self.assertEqual(multiply(-2, 3), -6)
    
    def test_divide(self):
        """Testa divisão."""
        self.assertEqual(divide(10, 2), 5)
        self.assertEqual(divide(7, 2), 3.5)
    
    def test_divide_by_zero(self):
        """Testa divisão por zero."""
        with self.assertRaises(ValueError):
            divide(5, 0)


class TestCalculator(unittest.TestCase):
    """Testes para a classe Calculator."""
    
    def setUp(self):
        """Configura o teste."""
        self.calc = Calculator()
    
    def test_execute_add(self):
        """Testa execução de adição."""
        result = self.calc.execute("+", 2, 3)
        self.assertEqual(result, 5)
    
    def test_execute_subtract(self):
        """Testa execução de subtração."""
        result = self.calc.execute("-", 5, 3)
        self.assertEqual(result, 2)
    
    def test_history(self):
        """Testa histórico."""
        self.calc.execute("+", 2, 3)
        self.calc.execute("*", 5, 4)
        
        history = self.calc.get_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["result"], 5)
        self.assertEqual(history[1]["result"], 20)
    
    def test_clear_history(self):
        """Testa limpeza de histórico."""
        self.calc.execute("+", 2, 3)
        self.calc.clear_history()
        
        self.assertEqual(len(self.calc.get_history()), 0)


if __name__ == "__main__":
    unittest.main()
