# Montarlo en GitHub, paso a paso

Tiempo: unos 20 minutos. Solo se hace una vez.

Al terminar: tu cliente abre una dirección web en el móvil y ve los datos.
Cada noche se actualizan solos. Ninguno de los dos toca nada.

---

## Lo que vas a montar

```
tu-repositorio/
├── index.html                        la app
├── data.json                         los partidos
├── scripts/
│   └── actualizar_datos.py           el que busca resultados nuevos
└── .github/workflows/
    └── actualizar.yml                el que lo lanza cada noche
```

Los cuatro archivos te los he dejado ya con esa estructura en la carpeta
`repo`. Solo hay que subirlos tal cual.

---

## Paso 1 — Crear el repositorio

1. En GitHub, botón **+** arriba a la derecha → **New repository**
2. Nombre: el que quieras, por ejemplo `marcador`
3. Visibilidad: **Public**

   Ponlo público. Con privado, GitHub Pages exige plan Pro de pago, y aquí
   no hay nada que ocultar: ni claves, ni datos personales, ni nada que no
   esté ya publicado en la web de origen.

4. No marques ninguna casilla de las de abajo (README, .gitignore, licencia)
5. **Create repository**

---

## Paso 2 — Subir los archivos

En la pantalla que sale, pulsa **uploading an existing file**.

Arrastra la carpeta `repo` entera, o los cuatro archivos respetando las
subcarpetas. GitHub mantiene la estructura si arrastras carpetas.

Comprueba antes de confirmar que ves las rutas completas:
`.github/workflows/actualizar.yml` y `scripts/actualizar_datos.py`.
Si `actualizar.yml` acaba en la raíz en vez de dentro de `.github/workflows`,
la tarea automática no se ejecutará nunca y no habrá ningún aviso.

Abajo, **Commit changes**.

---

## Paso 3 — Permitir que el robot guarde los cambios

Sin esto, la tarea se ejecuta pero no puede guardar nada y falla al final.

1. Pestaña **Settings** del repositorio
2. Menú izquierdo: **Actions** → **General**
3. Baja hasta **Workflow permissions**
4. Marca **Read and write permissions**
5. **Save**

---

## Paso 4 — Publicar la web

1. **Settings** → menú izquierdo **Pages**
2. En *Source*, elige **Deploy from a branch**
3. Branch: **main**, carpeta: **/ (root)**
4. **Save**

Espera un par de minutos y recarga esa misma página: aparecerá la dirección,
con la forma `https://TUUSUARIO.github.io/marcador/`

Ábrela. Deberías ver la app con 20 partidos ya cargados.

---

## Paso 5 — Probar la actualización a mano

No esperes a mañana para saber si funciona.

1. Pestaña **Actions** del repositorio
2. En la izquierda, **Actualizar resultados**
3. Botón **Run workflow** → **Run workflow**
4. Recarga a los 30 segundos y entra en la ejecución

**Si sale verde:** funciona. Mira `data.json` en el repositorio; si ha
encontrado partidos nuevos, tendrá más de 20.

**Si sale rojo:** pincha en la ejecución y lee el paso que ha fallado.

- *"No se ha reconocido ningún partido"* → la web de origen ha cambiado su
  estructura. Hay que ajustar los patrones que están al principio de
  `scripts/actualizar_datos.py`. Pásame el mensaje y te digo qué cambiar.
- *Error al hacer push* → te has saltado el paso 3.

---

## Paso 6 — Dárselo a tu cliente

Le pasas la dirección. Que la abra en el móvil y la añada a la pantalla de
inicio:

- **iPhone**: en Safari, botón de compartir → *Añadir a pantalla de inicio*
- **Android**: en Chrome, menú de tres puntos → *Añadir a pantalla de inicio*

Esto no es un capricho estético. En iPhone, Safari borra los datos guardados
de una web tras 7 días sin abrirla; las webs añadidas a la pantalla de inicio
quedan exentas de ese borrado.

---

## Lo que hay que vigilar

**Las tareas programadas se desactivan solas.** GitHub las apaga cuando un
repositorio pasa 60 días sin actividad, y los guardados que hace el propio
robot no cuentan como actividad. Recibirás un correo avisando, y se
reactivan con un clic desde la pestaña Actions. Si no quieres depender de
eso, entra cada mes o dos y lanza el workflow a mano: eso reinicia el
contador.

**Si el scraper deja de reconocer partidos, la ejecución sale en rojo.**
Está hecho así a propósito: prefiero que falle de forma visible y GitHub te
mande un correo, a que siga guardando un archivo vacío y la app muestre
datos de hace tres meses como si fueran de hoy.

**Cuando cambie la versión del juego** (cada septiembre sale una nueva), los
resultados de la anterior dejan de ser comparables: cambia el meta y el
ritmo goleador. Los partidos viejos siguen en la base y seguirán contando
para el marcador entre dos jugadores, que es lo que a tu cliente le
interesa, pero conviene tenerlo presente al mirar las líneas de goles.

---

## Y lo que sigue pendiente

Verificar si los marcadores que llegan son de partido único o agregados de
ida y vuelta. En los datos que tengo hay resultados de 12-6 y 11-4, que dan
totales de 18 y 15 goles. Si son agregados de dos partidos, todas las líneas
de goles que vea tu cliente estarán calculadas sobre el doble de lo real.

Es la única pieza que no puedo comprobar yo, y es la que más dinero puede
costar. Que mire dos o tres de esos partidos en la ficha del torneo y salga
de dudas antes de apostar un euro a un "menos de".
