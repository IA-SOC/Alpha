# US23: kit de identidad visual ALIGO

Preparado el 26-10-2026 para SOC AI Analyst.

## Qué puedes hacer ahora

1. Descomprime el ZIP y abre `referencia-visual.html` en el navegador. Funciona sin conexión.
2. Revisa los logos, colores, tipografía y estilos de controles.
3. Comparte el paquete con Roberto para acordar su integración. El paquete está preparado; no se ha enviado a nadie.
4. Mantén la tarea en progreso hasta aplicarla y revisarla en las pantallas reales.

## Qué contiene

- `assets/logos/`: los dos PNG originales recibidos, sin modificar.
- `assets/fonts/`: Poppins Regular, Bold, Italic, Medium y Medium Italic originales.
- `styles/aligo.css`: fuentes locales, colores y clases para botones, tarjetas, campos, foco de teclado y lectura clara.
- `referencia-visual.html`: catálogo visual de marca, sin casos, alertas ni reportes.
- `docs/GUIA_MARCA_RECIBIDA.md`: copia de la guía recibida para consultar su origen.
- `docs/INTEGRACION.md`: instrucciones y pendientes de integración.
- `assets/fonts/LICENCIAS_ORIGEN.md`: aviso de licencias recibido con los recursos.

## Decisiones de preparación

- Negro #000000 dominante y rojo #E63340 como acento; gris #4C5356 y blanco #FFFFFF como base.
- Poppins Regular sustituye provisionalmente a Poppins Light, que no está incluida. No se simula el peso 300.
- Se usa rojo oscuro #C80E28 para la base del botón; el hover usa rojo #E63340 con texto de 18 px y peso 700. Es una decisión de interfaz que favorece el contraste.
- Los estilos están limitados a `.aligo-ui` para facilitar la integración sin afectar elementos externos.
- No se incluyen Ubuntu, la plantilla Word ni íconos inventados como si fueran oficiales.
- El catálogo no incorpora lógica del producto. Las acciones solo muestran estilos y el campo permite revisar su apariencia y foco.

## Estado

Preparación de recursos completada. US23 continúa pendiente de integración, revisión responsive y validación sobre el frontend definitivo. Este paquete no modifica el repositorio ni sustituye el frontend de Roberto.
