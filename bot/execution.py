# Función para resetear cash reservado al inicio de cada iteración
def reset_reserved_cash():
    """Resetea el contador de cash reservado. Llamar al inicio de cada iteración."""
    global _reserved_cash
    old_reserved = _reserved_cash
    _reserved_cash = 0.0
    if old_reserved > 0:
        logger.info(f"🔄 Cash reservado reseteado: ${old_reserved:.2f} → $0.00")

# Función para obtener cash disponible real
def get_available_cash():
    """Retorna el cash realmente disponible para trading."""
    try:
        client = _client()
        account = client.get_account()
        total_cash = float(account.cash)
        available = total_cash * 0.9 - _reserved_cash
        return max(0, available), total_cash
    except Exception as e:
        logger.error(f"❌ Error obteniendo cash disponible: {e}")
        return 0.0, 0.0

# bot/execution.py