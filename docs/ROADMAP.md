# Roadmap

## Phase 1 — Foundation (implemented)

- Workspace, experimental Rust block cipher, Python reference, vector, basic reversibility checks, small avalanche probe, CLI demonstration, and security documentation.
- Rust compiled and tested locally on Windows GNU; Python and Rust agree on 185 shared vectors. See `ITERATION_2026_10_11.md` for the recorded checks.

## Phase 2 — Cryptoanalysis (started)

Implemented: labelled round variants, shared fixtures, exact S-box DDT/Walsh/nonlinearity, descriptive block/key avalanche and SAC/BIC estimates, per-round diffusion, and a small repeated-byte key-schedule probe. Methodology and raw results are published. Full-network attack analysis remains open.

Added: a fully specified 16-bit toy model with exact fixed-key differentials for selected input differences and linear correlations for selected output masks, exhaustive plaintext coverage, witnesses and a random permutation reference. This is distinct from reduced-round analysis of the full-width cipher; see `REDUCED_MODEL.md`.

1. Freeze the specification and add independent vector generation/cross-checking before interpreting measurements.
2. Add S-box metrics: differential distribution table, maximum differential probability, linear approximation table, and component nonlinearity.
3. Measure block and key avalanche, SAC, and bit-independence over stated sample sizes and fixed seeds; publish scripts and raw result metadata.
4. Build reduced-round experiments and exhaustive small-width models for differential/linear trail search, round dependencies, and key-schedule collisions or equivalence.
5. Add reproducible Rust benchmarks and compare AES-256/ChaCha20 only with documented libraries, modes/interfaces, hardware, versions, and methodology. Do not infer security from speed or statistical appearance.
6. Seek external cryptanalysis and record negative results without tuning metrics as a substitute for a security argument.

## Phase 3 — Original protocol research prototype

The direction was revised on 2026-10-11 to use the original NA&STY-X construction. See `PROTOCOL_DESIGN.md` for the current design boundary.

1. Improve and analyze the custom S-box, full round function and key schedule; record weaknesses without claiming security from statistics.
2. Specify and analyze message encryption, authentication and key separation individually before implementing them.
3. Specify canonical serialization, pre-established secret-key assumptions, per-direction states, uniqueness across restarts, replay handling and errors.
4. Implement a small research two-party prototype with negative tests and interoperability vectors. It is not approved for real secrets.
5. Key establishment, forward secrecy, multiple devices, groups and post-quantum properties remain separate open problems requiring explicit analysis.

## Current v0.2 milestone

AES substitution was removed from the active cipher. A public 12-round nibble-Feistel generator and exhaustive screening of 256 candidates produce the selected table. Candidate 18 has DU 10 and minimum component nonlinearity 96: weaker than the prior S-box. Its initial screening target was not met. Research continues; full-network attack bounds and independent cryptanalysis remain missing.

## NXS1 — первый E2EE-прототип

Следующая выполненная итерация: точное full-width related-round-key тождество,
ограниченный поиск 8192 пар мастер-ключей, синтаксически корректные попытки подделки
NXM3 и контроль компрометации цепочки. Активная Rust S-box заменена эквивалентной ANF
без secret-indexed loads; её цена по скорости и одна ASM-сборка опубликованы.
Это не устраняет структурное тождество и не доказывает стойкость. См. `CONSTRUCTION_ANALYSIS.md`.

Связывание через одноразовый случайный секрет, код сверки, направленные цепочки, replay/
reorder и закрытие сеанса реализованы. Rust/Python совместимы; есть трёхпроцессная
интерактивная демонстрация. Перезапуск и восстановление после компрометации требуют нового
внешнего секрета. Дополнительное устройство — отдельный сеанс, без готового multi-device сервиса.

Открыты: полноразмерный криптоанализ ядра/тега/KDF, внешняя экспертиза, защищённая память/
хранилище, реальные сбои и своё установление ключей без доверенного канала. Автоматическая
PCS, гарантированная прямая секретность и защита реальных секретов не считаются выполненными.

## v0.3 — исторический инженерный этап

Добавлены улучшенная собственная таблица (DU 8, NL 102), три ARX-преобразования, нелинейное расписание, реальные полноразмерные выборочные проверки, новый точный toy-анализ и измерение скорости. Реализованы сообщения произвольной длины с экспериментальным тегом, разделением ключей и persistent nonce-реестром; отсутствие состояния больше не приводит к автоматическому сбросу. Это завершает текущую исследовательскую реализацию этапов ядра и сообщений, но не закрывает все криптоаналитические вопросы или пригодность для реальных секретов. Сессионный протокол остаётся следующим этапом.
