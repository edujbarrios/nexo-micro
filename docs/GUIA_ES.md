# Guía en español — NEXO Micro

NEXO Micro es una **librería Python open source (MIT)** y un lenguaje experimental de mensajes mínimos para agentes de IA. **No cifra**, no comprime cualquier texto y no garantiza ahorro universal de tokens.

## Diferencia respecto a NEXO

- NEXO transmite estructuras arbitrarias de forma reversible.
- NEXO Micro transmite un conjunto pequeño de **intenciones compartidas**. Puede omitir identificadores repetidos porque ambos agentes conocen el contexto.
- Si quieres transmitir una conversación libre, NEXO Micro no es suficiente: usa texto/JSON u otro protocolo.

## Primera prueba

```bash
python -m pip install -e .
python -m nexo_micro demo
```

```python
from nexo_micro import MicroSession

a = MicroSession()
b = MicroSession()
wire = a.encode({"task": 42, "intent": "complete", "critical": 3})
print(wire)  # @16|!3
assert b.decode(wire) == {"task": 42, "intent": "complete", "critical": 3}
```

Para un ejemplo de agentes conectados y negociando diccionario: `python examples/handshake_agents.py`. Una aplicación real tiene que transportar los mensajes con TLS autenticado y manejar quién puede ejecutar cada acción.

## Cómo comprobar el ahorro

```bash
python -m pip install -e '.[bench]'
python -m nexo_micro bench --encoding o200k_base --repeats 100
python -m nexo_micro bench --encoding cl100k_base --repeats 100
```

El benchmark incluye JSON completo, JSON con campos mínimos, JSON con estado y NEXO Micro. También informa del coste de enseñar el lenguaje una vez al modelo. **Solo mide recuentos del tokenizador, no la capacidad real de los modelos para comprender ni producir los mensajes.** La eficacia real requiere medir prompts completos, respuestas, errores y reintentos con modelos reales.

## Publicación

La distribución en PyPI se llama `nexo-micro`; la importación es `nexo_micro`. Consulta [la guía de publicación](PYPI.md). Publicar requiere una cuenta PyPI y configurar el enlace seguro de GitHub Actions (Trusted Publishing).
