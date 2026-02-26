import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

enum MemoryType {
  identity,
  family,
  name,
  place,
  hobby,
  preference,
  task,
  plan,
  goal,
  conversation,
  other,
}

class MemoryItem {
  final String id;
  final MemoryType type;
  final String key;
  final String value;
  final DateTime createdAt;
  final DateTime updatedAt;
  final int mentions;

  const MemoryItem({
    required this.id,
    required this.type,
    required this.key,
    required this.value,
    required this.createdAt,
    required this.updatedAt,
    required this.mentions,
  });

  MemoryItem copyWith({
    String? value,
    DateTime? updatedAt,
    int? mentions,
  }) {
    return MemoryItem(
      id: id,
      type: type,
      key: key,
      value: value ?? this.value,
      createdAt: createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      mentions: mentions ?? this.mentions,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'type': type.name,
      'key': key,
      'value': value,
      'createdAt': createdAt.toIso8601String(),
      'updatedAt': updatedAt.toIso8601String(),
      'mentions': mentions,
    };
  }

  static MemoryItem fromJson(Map<String, dynamic> json) {
    return MemoryItem(
      id: json['id'] as String,
      type: MemoryType.values.firstWhere(
        (type) => type.name == (json['type'] as String? ?? 'other'),
        orElse: () => MemoryType.other,
      ),
      key: json['key'] as String,
      value: json['value'] as String,
      createdAt: DateTime.parse(json['createdAt'] as String),
      updatedAt: DateTime.parse(json['updatedAt'] as String),
      mentions: (json['mentions'] as num?)?.toInt() ?? 1,
    );
  }
}

class MemoryStore {
  static const String _memoryKey = 'human_memory_items_v2';
  static const String _historyKey = 'human_memory_history_v2';

  final List<MemoryItem> _items = <MemoryItem>[];
  final List<String> _history = <String>[];

  List<MemoryItem> get items => List<MemoryItem>.unmodifiable(_items);

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();

    final rawItems = prefs.getString(_memoryKey);
    if (rawItems != null && rawItems.isNotEmpty) {
      final decoded = jsonDecode(rawItems) as List<dynamic>;
      _items
        ..clear()
        ..addAll(
          decoded
              .map((item) => MemoryItem.fromJson(Map<String, dynamic>.from(item as Map)))
              .toList(growable: false),
        );
    }

    final rawHistory = prefs.getStringList(_historyKey);
    if (rawHistory != null) {
      _history
        ..clear()
        ..addAll(rawHistory);
    }
  }

  Future<void> save() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _memoryKey,
      jsonEncode(_items.map((item) => item.toJson()).toList()),
    );
    await prefs.setStringList(_historyKey, _history.take(80).toList());
  }

  Future<void> clear() async {
    _items.clear();
    _history.clear();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_memoryKey);
    await prefs.remove(_historyKey);
  }

  void ingestUserMessage(String text) {
    final input = text.trim();
    if (input.isEmpty) {
      return;
    }

    _history.insert(0, 'User: $input');
    if (_history.length > 80) {
      _history.removeLast();
    }

    _extractMemory(input);
    _upsert(
      type: MemoryType.conversation,
      key: 'last_user_message',
      value: input,
    );
  }

  void ingestAssistantMessage(String text) {
    final input = text.trim();
    if (input.isEmpty) {
      return;
    }

    _history.insert(0, 'Assistant: $input');
    if (_history.length > 80) {
      _history.removeLast();
    }

    _upsert(
      type: MemoryType.conversation,
      key: 'last_assistant_message',
      value: input,
    );
  }

  String buildMemoryContext(String query) {
    final tokens = query
        .toLowerCase()
        .split(RegExp(r'[^a-z0-9]+'))
        .where((token) => token.length > 2)
        .toSet();

    final sorted = <MemoryItem>[..._items]
      ..sort((a, b) => b.updatedAt.compareTo(a.updatedAt));

    final relevant = <MemoryItem>[];
    for (final item in sorted) {
      final combined = '${item.key} ${item.value}'.toLowerCase();
      final score = tokens.where(combined.contains).length;
      if (score > 0 || relevant.length < 8) {
        relevant.add(item);
      }
      if (relevant.length >= 14) {
        break;
      }
    }

    final memoryLines = relevant
        .map((item) => '[${item.type.name}] ${item.key}: ${item.value}')
        .join('\n');

    final recentHistory = _history.take(10).join('\n');

    return '''
PERSONAL MEMORY SNAPSHOT
$memoryLines

RECENT CONVERSATION HISTORY
$recentHistory
''';
  }

  void _extractMemory(String input) {
    final lower = input.toLowerCase();

    final nameMatch = RegExp(r'my name is\s+([a-zA-Z .-]+)', caseSensitive: false)
        .firstMatch(input);
    if (nameMatch != null) {
      _upsert(
        type: MemoryType.name,
        key: 'user_name',
        value: nameMatch.group(1)!.trim(),
      );
    }

    final liveMatch = RegExp(r'i live in\s+([a-zA-Z0-9 ,.-]+)', caseSensitive: false)
        .firstMatch(input);
    if (liveMatch != null) {
      _upsert(
        type: MemoryType.place,
        key: 'home_location',
        value: liveMatch.group(1)!.trim(),
      );
    }

    final hobbyMatch = RegExp(r'i (?:like|love|enjoy)\s+([a-zA-Z0-9 ,.-]+)',
            caseSensitive: false)
        .firstMatch(input);
    if (hobbyMatch != null) {
      _upsert(
        type: MemoryType.hobby,
        key: 'hobby',
        value: hobbyMatch.group(1)!.trim(),
      );
    }

    final preferenceMatch =
        RegExp(r'i prefer\s+([a-zA-Z0-9 ,.-]+)', caseSensitive: false)
            .firstMatch(input);
    if (preferenceMatch != null) {
      _upsert(
        type: MemoryType.preference,
        key: 'preference',
        value: preferenceMatch.group(1)!.trim(),
      );
    }

    final goalMatch =
        RegExp(r'(?:my goal is|i want to)\s+(.+)', caseSensitive: false)
            .firstMatch(input);
    if (goalMatch != null) {
      _upsert(
        type: MemoryType.goal,
        key: 'goal',
        value: goalMatch.group(1)!.trim(),
      );
    }

    final planMatch = RegExp(r'i plan to\s+(.+)', caseSensitive: false).firstMatch(input);
    if (planMatch != null) {
      _upsert(
        type: MemoryType.plan,
        key: 'plan',
        value: planMatch.group(1)!.trim(),
      );
    }

    final taskMatch =
        RegExp(r'(?:task|todo)\s*:\s*(.+)', caseSensitive: false).firstMatch(input);
    if (taskMatch != null) {
      _upsert(
        type: MemoryType.task,
        key: 'task',
        value: taskMatch.group(1)!.trim(),
      );
    }

    if (lower.contains('family')) {
      _upsert(
        type: MemoryType.family,
        key: 'family_note',
        value: input,
      );
    }

    if (lower.startsWith('remember that ')) {
      _upsert(
        type: MemoryType.other,
        key: 'remembered_fact',
        value: input.replaceFirst(RegExp(r'(?i)^remember that\s+'), '').trim(),
      );
    }
  }

  void _upsert({
    required MemoryType type,
    required String key,
    required String value,
  }) {
    final now = DateTime.now();
    final index = _items.indexWhere((item) => item.key == key && item.type == type);

    if (index == -1) {
      _items.add(
        MemoryItem(
          id: '${type.name}_$key',
          type: type,
          key: key,
          value: value,
          createdAt: now,
          updatedAt: now,
          mentions: 1,
        ),
      );
      return;
    }

    final current = _items[index];
    _items[index] = current.copyWith(
      value: value,
      updatedAt: now,
      mentions: current.mentions + 1,
    );
  }
}
