# NAXI — анимация логотипа

Текущий эскиз анимации: вихрь собирает большой знак N, отдельная прыгающая точка рисует NAXI. Последняя I плавно уменьшается, а зелёная точка становится над ней. Финальная надпись — NAXi. На этом рисование заканчивается. Большой знак пока использует предыдущую геометрию; новая форма ожидает выбора из пяти концепций в `assets/branding/naxi/concepts` репозитория.

## Готовые файлы

| Файл | Назначение |
| --- | --- |
| `assets/naxi-intro.json` | Заставка 6,17 секунды, прозрачный фон |
| `assets/naxi-intro-dark.json` | Та же заставка на графитовом фоне |
| `assets/naxi-idle.json` | Бесшовное ожидание 2,4 секунды, прозрачный фон |
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

- 0–1,30 с: вихрь из точек и изогнутых шлейфов.
- 1,08–1,83 с: формирование полного N.
- 1,95–5,07 с: прыгающая точка рисует NAXI.
- 5,07–5,57 с: I уменьшается, зелёная точка становится точкой маленькой i.
- 5,57–6,17 с: неподвижное финальное NAXi.

## Исходники

`source/build_motion.py` создаёт четыре JSON, локальные данные плеера и JSX. Запуск: `py -3 source/build_motion.py`. Геометрия хранится в `source/geometry.json`.

`source/capture.cjs` покадрово воспроизводит реальный JSON через lottie-web в Edge и создаёт контактный лист. Для него нужны Node.js, Playwright и Sharp. `source/batch-export.jsx` сохраняет AEP в отдельном пустом экземпляре After Effects.

Проверено воспроизведение через lottie-web 5.13.0 (SVG), все 370 кадров, открытие и сохранение исходника в After Effects 2025. Проверка HyperFrames завершена без ошибок. Служебные отчёты находятся в `qa/`.

Библиотеки плеера: lottie-web (MIT), GSAP — лицензии приложены к локальным файлам. GSAP используется только оболочкой Studio, сама анимация целиком находится в Lottie JSON.
