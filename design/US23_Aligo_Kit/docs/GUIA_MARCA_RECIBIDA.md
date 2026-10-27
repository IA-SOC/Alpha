---
name: marca-aligo
description: Identidad visual de ALIGO Defensores Informáticos S.A.S según su Manual de Identidad (Guía visual 2025). Úsala siempre que se cree o modifique cualquier pieza con la marca ALIGO, de cualquier tipo: interfaces web o de aplicaciones, componentes, CSS o Tailwind, correos HTML, informes y documentos Word, hojas de cálculo, presentaciones, diagramas o imágenes. Contiene la paleta oficial (principal, complementaria y de equipos) con códigos Pantone, CMYK, RGB y hex, las reglas del logo (versiones, área de reserva, tamaño mínimo, usos sobre fondos), la tipografía (Poppins), tokens listos para CSS y Tailwind, y una plantilla Word con su biblioteca en Python. Actívala también cuando se pidan "los colores de ALIGO", "el formato ALIGO", "la letra de la marca", "el logo" o los colores de un Team (Blue, Purple, Green, Red).
---

# Marca ALIGO

Guía de identidad visual de **ALIGO Defensores Informáticos S.A.S**, basada en su **Manual de Identidad
(Guía visual 2025)**. El concepto de la marca es **transformar lo complejo en algo simple**: piezas limpias,
pocos elementos y mucho contraste. Sirve para cualquier proyecto y no depende de ningún producto.

Regla rápida: **negro dominante, rojo #E63340 como acento, gris #4C5356 de apoyo, blanco para respirar,
Poppins en todo.**

> Fuente de verdad: el Manual de Identidad de ALIGO. Si algo de esta guía contradice el manual vigente,
> manda el manual. Los valores marcados como **heredado** o **funcional** no están en el manual: vienen de
> las plantillas actuales o se derivan para interfaces, y se usan solo donde se indica.

## Contenido de la skill

| Ruta | Qué es |
|---|---|
| `assets/logos/logo-aligo-color.png` | Logosímbolo en español, versión a color (rojo y gris) para fondo blanco, 1081×1081 px |
| `assets/logos/logo-aligo-blanco.png` | Logosímbolo a una tinta en blanco, 549×230 px, para fondos negros o de color |
| `assets/fuentes/` | Poppins, Poppins Medium y Ubuntu (TTF completos, licencias libres; ver `assets/fuentes/LICENCIAS.md`) |
| `assets/plantillas/plantilla_aligo.docx` | Plantilla Word actual: encabezado con logo, pie de propiedad, estilos y fuentes incrustadas |
| `scripts/aligo_docx.py` | Biblioteca Python (python-docx) para generar documentos con la plantilla |

Las demás versiones del manual (logosímbolo en inglés, símbolo solo, versiones en degradado, logos de
servicios, iconografía, plantillas de diapositivas) no están incluidas: pedirlas al área de marca de ALIGO.

## 1. Paleta de colores

### Principal

| Color | Pantone | CMYK | RGB | Hex | Papel |
|---|---|---|---|---|---|
| **Negro puro** | Black 6 C | 91, 79, 62, 97 | 0, 0, 0 | `#000000` | **Dominante**: fondo principal de la marca |
| **Deep Carmine Pink** (rojo ALIGO) | Red 032 C | 0, 78, 72, 10 | 230, 51, 64 | `#E63340` | Color de marca y acento |
| **Davy's Grey** | 7540 C | 12, 3, 0, 66 | 76, 83, 86 | `#4C5356` | Gris de marca, apoyo y texto secundario |
| **White** | 447 C (según el manual) | 0, 0, 0, 0 | 255, 255, 255 | `#FFFFFF` | Fondo claro y texto sobre negro |

### Complementaria

| Familia | Oscuro | Medio | Principal | Claro |
|---|---|---|---|---|
| Rojo | `#C80E28` | `#E3032C` | `#E63340` | `#EC6670` |
| Gris | `#313535` | `#4C5356` (principal) | `#787979` | `#ACADAD` |

Usos sugeridos: `#C80E28` para fondos rojos con texto blanco y para estados hover o activos; `#EC6670` para
detalles suaves sobre negro; `#313535` para superficies elevadas sobre negro (tarjetas, menús); `#787979` y
`#ACADAD` para texto auxiliar, bordes y separadores.

### Paletas de equipos y áreas

Solo para piezas específicas de cada equipo o área. El **Red Team** usa la paleta complementaria del rojo.

| Equipo o área | Oscuro | Medio | Claro | Muy claro |
|---|---|---|---|---|
| **Blue Team** y Bienestar ALIGO | `#236688` | `#2E87B5` | `#96C3DA` | `#BFDAE8` |
| **Purple Team**, Cultura ALIGO y HyphatIA | `#8033E5` | `#985CEA` | `#A570ED` | `#D8C1F7` |
| **Green Team** | `#006032` | `#409F72` | `#B2EBCF` | `#CBF1DF` |

### Estados en interfaces (funcional)

El manual no define colores de estado. Para interfaces se derivan así, priorizando la paleta oficial:

| Estado | Fuerte (texto, borde, icono) | Fondo suave | Origen |
|---|---|---|---|
| Error, crítico | `#C80E28` | `#FBE3E5` | Complementaria roja; fondo derivado |
| Correcto | `#006032` | `#CBF1DF` | Paleta Green Team |
| Información | `#236688` | `#BFDAE8` | Paleta Blue Team |
| Advertencia | `#B9770E` | `#FCE9CE` | Funcional, fuera del manual (no hay amarillo oficial) |

### Contraste (WCAG)

- Texto blanco sobre `#000000`, `#313535` o `#4C5356`: cumple AA.
- Texto blanco sobre `#C80E28`: cumple AA para cualquier tamaño.
- Texto blanco sobre `#E63340`: solo texto grande o negrita (botones, títulos). Para párrafos sobre rojo, usar `#C80E28`.
- Rojo `#E63340` sobre negro: cumple AA para títulos y destacados.
- Texto corrido sobre blanco: `#000000` o `#313535`.

## 2. Logo

- **Versión principal: sobre fondo negro.** También existe la versión principal sobre fondo blanco
  (`logo-aligo-color.png`), y el logosímbolo en **español** («ALIGO Defensores Informáticos») y en **inglés**.
- **Fondos de color** (complementarios o de equipo): usar siempre el logosímbolo o el símbolo **a una sola
  tinta** (blanco o negro, según el contraste).
- **Degradados** del símbolo (con relleno o en contornos): **solo sobre fondos negros**.
- **Área de reserva**: como mínimo, el **ancho de la letra «O»** del logosímbolo, libre alrededor.
- **Tamaño mínimo de impresión**: logosímbolo **12 mm de alto**; símbolo solo **10 mm de alto**. En
  pantalla, no bajar de unos 48 px de alto para el logosímbolo.
- **Eslogan**: el logosímbolo lleva el eslogan debajo de ALIGO. Variantes del manual: «Defensores
  informáticos» y «Seguridad de la información». **No cambiar el eslogan de lugar** ni reemplazarlo por otro texto.
- **Usos indebidos** (según el manual):
  - No distorsionar la forma.
  - No modificar la forma de ningún elemento.
  - No modificar el color.
  - No usar textos alternativos en lugar del eslogan.
  - No añadir elementos que no hagan parte del logo.
  - No cambiar el eslogan de lugar.
  - No usar sobre colores que no son de la marca.
  - No usar sobre fondos que no generen contraste.

### Logos de servicios
Los servicios de ALIGO (por ejemplo, **TheDeep**) tienen logo propio en **negro y rojo**, con versión sobre
fondo negro y sobre fondo blanco. Se aplican las mismas reglas de área de reserva, tamaño mínimo y usos
indebidos. Los archivos se piden al área de marca.

## 3. Tipografía

**Poppins** en todas las piezas, con estos roles (según el manual):

| Uso | Fuente |
|---|---|
| Títulos y subtítulos | **Poppins Bold** |
| Subtítulos, destacados y usos especiales | **Poppins Italic**, en pesos Bold, Medium o Light (en el ejemplo del manual, el subtítulo va en Poppins Medium Italic) |
| Cuadros de texto y texto corrido | **Poppins Light** |

- **Interlineado**: al menos **5 puntos más que el tamaño de la letra** en todos los textos (títulos,
  subtítulos, destacados y cuadros de texto). Ejemplos: texto de 10 pt con interlineado de 15 pt; título de
  24 pt con interlineado de 29 pt. En CSS: `line-height: calc(1em + 5pt)` o el valor equivalente en px.
- **Ejemplo del manual**: título en Poppins Bold, subtítulo en Poppins Medium Italic, párrafo en Poppins Light.
- Escala sugerida (no está en el manual): títulos 24 a 28 pt, subtítulos 14 a 16 pt, texto 10 a 11 pt en
  documentos; en pantalla, título 28 px, subtítulo 20 px, texto 15 a 16 px.
- Descarga libre en Google Fonts: https://fonts.google.com/specimen/Poppins
- Web: `https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,300;0,500;0,700;1,300;1,500;1,700&display=swap`
  (Light, Medium y Bold, con sus itálicas). Respaldo: `"Poppins", "Segoe UI", Roboto, Helvetica, Arial, sans-serif`.
- `assets/fuentes/` trae Poppins Regular, Bold, Italic, Bold Italic y Poppins Medium (las que usa la plantilla
  Word). **Poppins Light** y las demás itálicas se descargan de Google Fonts.
- **Ubuntu** solo viene incrustada en la plantilla Word; no forma parte del manual.

## 4. Tokens

### CSS

```css
:root {
  /* Principal */
  --aligo-negro: #000000;        /* dominante */
  --aligo-rojo: #E63340;         /* Pantone Red 032 C */
  --aligo-gris: #4C5356;         /* Pantone 7540 C */
  --aligo-blanco: #FFFFFF;
  /* Complementaria */
  --aligo-rojo-oscuro: #C80E28;  --aligo-rojo-medio: #E3032C;  --aligo-rojo-claro: #EC6670;
  --aligo-gris-oscuro: #313535;  --aligo-gris-medio: #787979;  --aligo-gris-claro: #ACADAD;
  /* Estados (funcional) */
  --aligo-error: #C80E28;   --aligo-error-bg: #FBE3E5;
  --aligo-ok: #006032;      --aligo-ok-bg: #CBF1DF;
  --aligo-info: #236688;    --aligo-info-bg: #BFDAE8;
  --aligo-aviso: #B9770E;   --aligo-aviso-bg: #FCE9CE;
  --aligo-fuente: "Poppins", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
/* Roles tipográficos del manual: texto Light, títulos Bold, destacados Italic */
body { font-weight: 300; line-height: calc(1em + 5pt); }
h1, h2, h3 { font-weight: 700; line-height: calc(1em + 5pt); }
.destacado, .subtitulo { font-style: italic; font-weight: 500; }
/* Tema principal (negro dominante) */
body { font-family: var(--aligo-fuente); background: var(--aligo-negro); color: var(--aligo-blanco); }
/* Tema claro, para documentos y vistas de lectura larga */
.tema-claro { background: var(--aligo-blanco); color: var(--aligo-negro); }
```

### Tailwind (`tailwind.config.js`)

```js
theme: {
  extend: {
    colors: {
      aligo: {
        negro: "#000000", rojo: "#E63340", gris: "#4C5356", blanco: "#FFFFFF",
        "rojo-oscuro": "#C80E28", "rojo-medio": "#E3032C", "rojo-claro": "#EC6670",
        "gris-oscuro": "#313535", "gris-medio": "#787979", "gris-claro": "#ACADAD",
        error: "#C80E28", ok: "#006032", info: "#236688", aviso: "#B9770E",
      },
      "blue-team":   { 900: "#236688", 600: "#2E87B5", 300: "#96C3DA", 100: "#BFDAE8" },
      "purple-team": { 900: "#8033E5", 600: "#985CEA", 300: "#A570ED", 100: "#D8C1F7" },
      "green-team":  { 900: "#006032", 600: "#409F72", 300: "#B2EBCF", 100: "#CBF1DF" },
    },
    fontFamily: { sans: ["Poppins", "Segoe UI", "Roboto", "Helvetica", "Arial", "sans-serif"] },
  },
}
```

## 5. Iconografía

El manual tiene dos familias de iconos, **general** y **personalizada**, cada una en cuatro versiones:

| Versión | Dónde usarla |
|---|---|
| Degradado | Solo sobre fondo negro |
| Blanco | Sobre fondos oscuros o negros |
| Negro | Sobre fondos claros o blancos |
| Rojo `#E63340` | Según el contraste: sobre blanco o sobre negro |

Los archivos de iconos se piden al área de marca. Si hay que usar una librería abierta mientras tanto, elegir
un estilo de trazo simple y uniforme, y aplicarle estos mismos colores y reglas de fondo.

## 6. Aplicación por formato

### Interfaces web y aplicaciones
- **Tema principal oscuro**: fondo `#000000`, superficies `#313535`, texto blanco, texto auxiliar `#ACADAD`,
  logo principal (versión sobre negro).
- **Tema claro** (lectura larga, formularios extensos): fondo blanco, texto `#000000` o `#313535`, logo a color.
- Botón primario: fondo `#E63340`, texto blanco en negrita; hover y activo `#C80E28`.
- Botón secundario: borde y texto blanco sobre negro (o `#4C5356` sobre blanco), fondo transparente.
- Enlaces y foco: `#E63340` sobre negro; `#C80E28` sobre blanco.
- Bordes y separadores: `#4C5356` sobre negro, `#ACADAD` sobre blanco.
- Alertas: color fuerte del estado como borde izquierdo de 4 px e icono, con su fondo suave (tema claro) o
  `#313535` (tema oscuro).
- Piezas de un equipo: acentos con la paleta del equipo, manteniendo negro, gris y blanco como base.

### Presentaciones y piezas gráficas
- Fondos negros como opción principal, con el logo en versión sobre negro; títulos en blanco y un detalle en
  `#E63340`.
- Una idea por diapositiva, mucho espacio negativo.
- Gráficos: serie principal `#E63340`, comparativas `#787979` y `#ACADAD`; paletas de equipo solo en piezas de
  ese equipo.
- Los degradados del símbolo solo se usan sobre negro.

### Documentos Word (plantilla actual)
La plantilla incluida es la que ALIGO usa hoy para informes y guías. Fondo blanco (lectura e impresión):
- **Encabezado**: logo a color; «Gestión de Ingeniería», el nombre del proyecto, «Emisión» y la fecha
  (DD-MM-AAAA); clasificación (Uso Interno o Confidencial).
- **Pie**: aviso de propiedad de ALIGO S.A.S («COPIA NO CONTROLADA al imprimir») y número de página.
- **Portada**: título en Poppins 22 pt negrita, subtítulo en rojo, tabla «Concepto / Detalle» (Documento,
  Fecha de emisión, Elaborado por, Clasificación y filas propias).
- **Índice**, secciones numeradas (1., 1.1), tablas con encabezado rojo y texto blanco, notas con borde
  izquierdo de color, métricas destacadas.
- **Heredado**: la biblioteca usa `#C0392B` como rojo de tablas y notas. Es cercano al rojo oscuro oficial;
  para piezas nuevas fuera de esta plantilla, usar `#C80E28` o `#E63340`.

```python
import sys; sys.path.insert(0, "<ruta de la skill>/scripts")
from aligo_docx import DocAligo, VERDE, AZUL, ROJO, AMBAR

d = DocAligo("Título del documento", "Subtítulo", fecha="21-10-2026",
             clasificacion="Confidencial", proyecto="Nombre del proyecto")
d.portada(filas_meta=[("Cliente", "Nombre del cliente")])
d.indice()
d.h1("Resumen"); d.p("Texto con **negrita** y `código`.")
d.metricas([("99,7%", "disponibilidad", VERDE), ("3", "pendientes", AMBAR)])
d.tabla(["Columna A", "Columna B"], [["1", "2"]], anchos=[8, 8.5], titulo="Ejemplo")
d.nota("Importante", ["Texto de la nota."], tipo="alerta")   # info | alerta | aviso | ok
d.guardar("documento.docx")
```

Requiere `python-docx`. Con LibreOffice (`soffice`) y `pdftotext` el índice sale con números de página; sin
ellos, Word los calcula al abrir el documento (aceptar «Actualizar campos»).

### Hojas de cálculo (formato actual)
- Banda superior de unas 6 filas con el logo en blanco y el título en blanco, Poppins 15 pt negrita (el
  título empieza a la derecha del logo). **Heredado**: la banda actual usa coral `#EF404A`; para hojas
  nuevas, usar `#E63340` (o negro `#000000` con el logo principal).
- Encabezados de columna: fondo rojo oscuro (`#C80E28`; heredado `#C0392B`), texto blanco en negrita.
- Filas de sección: fondo `#ACADAD` claro o `#D9D9D9` (heredado), texto en negrita.
- Toda la hoja en Poppins 10 pt; formato condicional con los estados; leyenda de colores al final.

## 7. Redacción

- Español neutro y profesional, frases cortas y en voz activa: coherente con «transformar lo complejo en
  algo simple».
- **No usar la raya «—» ni la raya corta «–»** en ningún texto: usar dos puntos, comas, paréntesis o «a» en
  los rangos («de 8 a 12»). En títulos: «Producto: Guía de Operación».
- Fechas en texto como «21 de octubre de 2026»; en encabezados y metadatos, DD-MM-AAAA.
- Números con punto de miles y coma decimal: 1.250 · 99,7%.
- Nombre legal completo la primera vez: «ALIGO Defensores Informáticos S.A.S»; después, «ALIGO».
