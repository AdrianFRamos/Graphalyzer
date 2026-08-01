"""
Módulo calculadora - Operações matemáticas básicas.
"""


def add(a: float, b: float) -> float:
    """
    Soma dois números.
    
    Args:
        a: Primeiro número
        b: Segundo número
    
    Returns:
        A soma de a e b
    """
    return a + b


def subtract(a: float, b: float) -> float:
    """
    Subtrai dois números.
    
    Args:
        a: Primeiro número
        b: Segundo número
    
    Returns:
        A diferença entre a e b
    """
    return a - b


def multiply(a: float, b: float) -> float:
    """
    Multiplica dois números.
    
    Args:
        a: Primeiro número
        b: Segundo número
    
    Returns:
        O produto de a e b
    """
    return a * b


def divide(a: float, b: float) -> float:
    """
    Divide dois números.
    
    Args:
        a: Dividendo
        b: Divisor
    
    Returns:
        O quociente de a por b
    
    Raises:
        ValueError: Se b for zero
    """
    if b == 0:
        raise ValueError("Divisão por zero não é permitida")
    return a / b


class Calculator:
    """Calculadora com histórico de operações."""
    
    def __init__(self):
        """Inicializa a calculadora."""
        self.history = []
        self.result = 0
    
    def execute(self, operation: str, a: float, b: float) -> float:
        """
        Executa uma operação.
        
        Args:
            operation: Tipo de operação (+, -, *, /)
            a: Primeiro operando
            b: Segundo operando
        
        Returns:
            Resultado da operação
        """
        if operation == "+":
            self.result = add(a, b)
        elif operation == "-":
            self.result = subtract(a, b)
        elif operation == "*":
            self.result = multiply(a, b)
        elif operation == "/":
            self.result = divide(a, b)
        else:
            raise ValueError(f"Operação desconhecida: {operation}")
        
        self.history.append({
            "operation": operation,
            "a": a,
            "b": b,
            "result": self.result,
        })
        
        return self.result
    
    def get_history(self) -> list:
        """Retorna o histórico de operações."""
        return self.history
    
    def clear_history(self) -> None:
        """Limpa o histórico."""
        self.history = []
