"""Render a readable transcript from the actually executed public demo report."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
report = json.loads((ROOT / 'research/results/e2ee-demo-v1.json').read_text(encoding='utf8'))
lines = ['# NAXi / NA&STY-X — работающий E2EE-прототип', '',
         'Этот отчёт сформирован из выполненного трёхпроцессного сценария. '
         'Все тексты демонстрационные; это проверка поведения, не доказательство стойкости.', '',
         '```mermaid', 'sequenceDiagram', '    participant A as Клиент Alice',
         '    participant S as Relay: только пакеты', '    participant B as Клиент Bob',
         '    Note over A,B: Одноразовое связывание через отдельный доверенный канал',
         '    A->>S: Offer', '    S->>B: Offer', '    B->>S: Reply', '    S->>A: Reply',
         '    A->>S: Confirm', '    S->>B: Confirm',
         '    Note over A,B: Сверка кода собеседника',
         '    A->>A: Новый ключ сообщения + шифрование', '    A->>S: NXS1 ciphertext + tag',
         '    S->>B: NXS1 ciphertext + tag',
         '    B->>B: Проверка тега/повтора → расшифрование', '```', '',
         '## Трасса выполненного сценария', '', '| Событие | Результат |', '|---|---|']
for event in report['events']:
    details = event['details'].replace('|', '\\|').replace('\n', ' ')
    lines.append(f'| {event["event"]} | {details} |')
packets = report['relay_packets']
lines += ['', '## Что видел сервер', '',
          f'В журнале relay **{len(packets)} пакетов**. Каждая запись содержит только '
          '`to`, `packet` (hex) и `bytes`. '
          'Открытые тексты таблицы выше получены от клиентов доверенным локальным пультом, '
          'не из журнала relay.', '', 'Пример полной первой зашифрованной записи:', '', '```text']
first = next(item for item in packets if item['packet'].startswith('4e585331'))
lines += [first['packet'], '```', '', '## Запуск', '', 'Из C:\\Crypto:', '', '```powershell',
          'py -3 demos/e2ee_chat.py --interactive', '```', '',
          'После автоматического сценария вводи `alice текст` или `bob текст`. '
          'Команды `replay`, `tamper`, `reorder`, `renew`, `restart`, `status`, `quit` '
          'проверяют повторы, подмену, перестановку, новое связывание и сбой.', '',
          'Для повторного сохранения отчёта:', '', '```powershell',
          'py -3 demos/e2ee_chat.py --report research/results/e2ee-demo-v1.json',
          'py -3 research/summarize_e2ee_demo.py', '```', '', '## Ограничения применения', '',
          'Это готовый прототип для экспериментов и интеграции с тестовыми данными. '
          '**Реальную переписку защищать этой версией нельзя считать безопасным.** '
          'Нет независимого криптоанализа, гарантированного удаления/хранения ключей, '
          'асимметричного согласования или автоматической PCS. '
          'Первое связывание и восстановление требуют внешнего доверенного канала; '
          'после перезапуска история/ключи не восстанавливаются. '
          'Демо на одном компьютере не защищает от администратора/вредоносного ПО этой ОС.', '',
          'Точная спецификация: [SESSION_SPEC_V1.md](SESSION_SPEC_V1.md). '
          'Внешняя оценка: [REVIEW_REQUEST.md](REVIEW_REQUEST.md) (подготовлена, не выполнена).', '']
(ROOT / 'docs/E2EE_DEMO.md').write_text('\n'.join(lines), encoding='utf8')
print('docs/E2EE_DEMO.md generated from executed demo report')
