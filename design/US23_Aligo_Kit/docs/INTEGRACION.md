# Integración con el frontend

## Integración básica

1. Copiar `assets` y `styles` juntos a la carpeta pública del frontend, manteniendo sus rutas relativas.
2. Cargar la hoja de estilo global una vez, desde el punto de entrada de la aplicación.
3. Aplicar la clase `aligo-ui` al contenedor raíz. Para lectura clara, agregar también `aligo-light` al contenedor que la necesita.
4. Usar clases `aligo-button`, `aligo-button-secondary`, `aligo-card`, `aligo-field` y `aligo-notice` según corresponda.
5. Mantener cada campo asociado a su etiqueta y dar al logo un texto alternativo descriptivo.

```html
<link rel="stylesheet" href="/styles/aligo.css">
<div class="aligo-ui">
  <div class="aligo-logo-space">
    <img class="aligo-logo" src="/assets/logos/logo-aligo-blanco.png"
         alt="ALIGO Defensores Informáticos">
  </div>
  <button type="button" class="aligo-button">Continuar</button>
</div>
```

En React usar `className`. Si hay Tailwind o un sistema de componentes, mapear sus variables a los tokens `--aligo-*` y adaptar los componentes existentes. No es necesario reemplazarlos. Acordar con Roberto la ubicación de los archivos y resolver los estilos globales que ya existan.

## Reglas del logo

- Usar el logo blanco sobre negro y la versión a color sobre blanco.
- Mantener proporción, colores y eslogan; no recortar, recolorear ni añadir elementos.
- Conservar al menos el ancho de la letra O como área libre alrededor. El padding de 24 px es una base; verificar la reserva visual según el tamaño final.
- La guía sugiere unos 48 px mínimos de altura para el logosímbolo en pantalla. Comprobar la altura visible, especialmente en el PNG a color que tiene espacio blanco interno.

## Pendientes y coordinación

- Confirmar con Roberto las pantallas y componentes en los que se integrará la marca.
- Solicitar Poppins Light y los íconos oficiales si se requieren. No vienen incluidos en los recursos recibidos.
- Revisar licencias y avisos completos de las fuentes antes de la distribución final; se conserva el aviso recibido.
- Mantener la página de referencia fuera de las rutas funcionales de producción, o solo como catálogo interno.

## Verificación al cerrar US23

- Logos correctos y legibles en cada fondo, con proporción y reserva adecuadas.
- Poppins cargada localmente, sin solicitudes a Google Fonts.
- Colores y componentes coherentes en las pantallas acordadas.
- Verificar 375, 768 y 1440 px de ancho sin desbordamiento horizontal.
- Recorrer los controles con Tab, revisar foco visible y etiquetas.
- Comprobar contraste en los estados normal, hover, foco y deshabilitado.
- Confirmar que los estilos no alteran navegación ni comportamiento de los componentes.
- Adjuntar capturas de las pantallas finales a la issue y solicitar revisión del equipo.

Esta lista es para la integración final; no afirma que el frontend definitivo ya haya sido validado.
