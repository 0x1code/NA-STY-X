# NAXI — анимация логотипа

Анимация первого исходного знака N с круглым вырезом сверху. Знак плавно появляется, затем прыгающая зелёная точка рисует NAXI. Последняя I уменьшается, точка становится над ней, и надпись превращается в NAXi. На этом анимация заканчивается. Финальное состояние неподвижно.

## Готовые файлы

| Файл | Назначение |
| --- | --- |
| `assets/naxi-intro.json` | Заставка 5,08 секунды, прозрачный фон |
| `assets/naxi-intro-dark.json` | Та же заставка на графитовом фоне |
| `assets/naxi-idle.json` | Статичное ожидание 2,4 секунды, прозрачный фон |
| `assets/naxi-idle-dark.json` | Ожидание на графитовом фоне |
| `renders/NAXI-Intro.mp4` | Видео для просмотра, без прозрачности |
| `preview.html` | Локальный плеер с перемоткой и переключением режима |
| `after-effects/NAXI-Intro.aep` | Редактируемый проект After Effects 2025 |
| `after-effects/NAXI-Intro.jsx` | Создание композиции из векторных слоёв |

Холст 1254 × 1254, 60 кадров/с. Все буквы переведены в контуры. JSON не требует шрифтов, картинок, выражений или внешних ресурсов. Прозрачность вырезов настоящая: они показывают фон приложения.

## Подключение на сайте

```js
const intro = lottie.loadAnimation({
  container: document.querySelector('#logo'),
  renderer: 'svg',
  loop: false,
  autoplay: true,
  path: '/assets/naxi-intro.json',
});
intro.addEventListener('complete', () => {
  intro.destroy();
  lottie.loadAnimation({
    container: document.querySelector('#logo'),
    renderer: 'svg',
    loop: true,
    autoplay: true,
    path: '/assets/naxi-idle.json',
  });
});
```

Начало idle совпадает с финальным состоянием intro. Для настройки уменьшенного движения показывайте `assets/naxi-current-static.svg`. Мобильные Lottie-плееры используют тот же JSON; воспроизведение на Android и iOS отдельно не проверялось.

`preview.html` открывается напрямую в браузере, интернет не нужен. Для Studio: `npm install`, затем `npm run dev`. Для проверки композиции: `npm run check`.

## After Effects

Откройте AEP или выполните JSX через **File → Scripts → Run Script File**. Геометрия, движения, маски Add/Subtract и Trim Paths остаются редактируемыми. Фон — отдельный нижний слой. Проект сохранён в After Effects 2025; для старых версий используйте JSX. Изменения в AEP не обновляют JSON автоматически.

## Тайминг

- 0–0,75 с: плавное появление первого исходного N.
- 0,87–3,98 с: точка рисует NAXI.
- 3,98–4,48 с: I уменьшается, зелёная точка образует маленькую i.
- 4,48–5,08 с: неподвижный финальный NAXi.

## Исходники

`source/build_motion.py` создаёт четыре JSON, локальные данные плеера и JSX. Запуск: `py -3 source/build_motion.py`. Геометрия хранится в `source/geometry.json`.

`source/capture.cjs` покадрово воспроизводит реальный JSON через lottie-web в Edge и создаёт контактный лист. Для него нужны Node.js, Playwright и Sharp. `source/batch-export.jsx` сохраняет AEP в отдельном пустом экземпляре After Effects.

Проверено воспроизведение через lottie-web 5.13.0 (SVG), все 305 кадров, открытие и сохранение исходника в After Effects 2025. Проверка HyperFrames завершена без ошибок. Служебные отчёты находятся в `qa/`.

Библиотеки плеера: lottie-web (MIT), GSAP — лицензии приложены к локальным файлам. GSAP используется только оболочкой Studio, сама анимация целиком находится в Lottie JSON.
