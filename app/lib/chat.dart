import 'package:flutter/material.dart';

import 'backend_api.dart';
import 'chat_message.dart';
import 'memory_store.dart';

class ChatPage extends StatefulWidget {
  const ChatPage({super.key, required this.title});

  final String title;

  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _UiMessage {
  final String text;
  final bool isAssistant;
  final String? imageUrl;

  const _UiMessage({
    required this.text,
    required this.isAssistant,
    this.imageUrl,
  });
}

class _ChatPageState extends State<ChatPage> {
  final TextEditingController _messageController = TextEditingController();
  final TextEditingController _imageUrlController = TextEditingController();
  final BackendApiService _apiService = BackendApiService();
  final MemoryStore _memoryStore = MemoryStore();
  final List<_UiMessage> _conversation = <_UiMessage>[];

  bool _loading = false;
  bool _memoryReady = false;

  @override
  void initState() {
    super.initState();
    _initMemory();
  }

  Future<void> _initMemory() async {
    await _memoryStore.load();
    if (!mounted) {
      return;
    }
    setState(() {
      _memoryReady = true;
    });
  }

  @override
  void dispose() {
    _messageController.dispose();
    _imageUrlController.dispose();
    super.dispose();
  }

  Future<void> _fetchData(String query, {String? imageUrl}) async {
    try {
      final result = await _apiService.chatMemory(message: query, topK: 8);
      final citationText = result.citations.isEmpty
          ? ''
          : '\n\nCitations:\n${result.citations.map((c) => '- ${c.title} (${c.sourceUri})').join('\n')}';
      final composed = '${result.answer}$citationText';
      _appendAssistant(composed);
      _memoryStore.ingestAssistantMessage(composed);
      await _memoryStore.save();
    } catch (error) {
      _appendAssistant('Backend chat error: $error');
    }
  }

  void _appendAssistant(String text) {
    if (!mounted) {
      return;
    }

    setState(() {
      if (_conversation.isNotEmpty && _conversation.last.text == 'Loading...') {
        _conversation.removeLast();
      }
      _conversation.add(_UiMessage(text: text, isAssistant: true));
      _loading = false;
    });
  }

  Future<void> _onSubmit() async {
    final text = _messageController.text.trim();
    final imageUrl = _imageUrlController.text.trim();

    if (text.isEmpty || _loading) {
      return;
    }

    setState(() {
      _conversation.add(
        _UiMessage(
          text: text,
          isAssistant: false,
          imageUrl: imageUrl.isEmpty ? null : imageUrl,
        ),
      );
      _conversation.add(const _UiMessage(text: 'Loading...', isAssistant: true));
      _loading = true;
    });

    _messageController.clear();
    _imageUrlController.clear();

    _memoryStore.ingestUserMessage(text);
    await _memoryStore.save();

    await _fetchData(text, imageUrl: imageUrl.isEmpty ? null : imageUrl);
  }

  Future<void> _openMemorySheet() async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) {
        final items = _memoryStore.items;

        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'Human Mind Memory',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    TextButton(
                      onPressed: () async {
                        await _memoryStore.clear();
                        if (!mounted) {
                          return;
                        }
                        setState(() {});
                        Navigator.of(context).pop();
                      },
                      child: const Text('Clear'),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                if (items.isEmpty)
                  const Text('No memory captured yet.')
                else
                  Flexible(
                    child: ListView.builder(
                      shrinkWrap: true,
                      itemCount: items.length,
                      itemBuilder: (_, index) {
                        final item = items[index];
                        return ListTile(
                          dense: true,
                          title: Text('${item.type.name}: ${item.key}'),
                          subtitle: Text(item.value),
                          trailing: Text('x${item.mentions}'),
                        );
                      },
                    ),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildInputBar() {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 16),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0x552196F3)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x1A2196F3),
            blurRadius: 12,
            offset: Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        children: [
          TextField(
            controller: _messageController,
            onSubmitted: (_) => _onSubmit(),
            maxLines: null,
            decoration: const InputDecoration(
              border: InputBorder.none,
              hintText: 'Ask about your docs, tasks, goals, or preferences...',
            ),
          ),
          const Divider(height: 10),
          TextField(
            controller: _imageUrlController,
            maxLines: 1,
            decoration: const InputDecoration(
              border: InputBorder.none,
              hintText: 'Image URL (optional for multimodal chat)',
              prefixIcon: Icon(Icons.image_outlined),
            ),
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              ElevatedButton.icon(
                onPressed: _loading ? null : _onSubmit,
                icon: const Icon(Icons.send_rounded),
                label: const Text('Send'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title),
        centerTitle: true,
        backgroundColor: Colors.white,
        foregroundColor: const Color(0xFF0B3E75),
        actions: [
          IconButton(
            tooltip: 'Memory',
            onPressed: _openMemorySheet,
            icon: const Icon(Icons.psychology_alt_outlined),
          ),
        ],
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Color(0xFFE3F2FD),
              Color(0xFFFFFFFF),
              Color(0xFFEAF3FF),
            ],
          ),
        ),
        child: Column(
          children: [
            if (_conversation.isEmpty)
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 28, 24, 12),
                child: Text(
                  _memoryReady
                      ? 'Multimodal RAG + Human Memory is ready.'
                      : 'Loading memory...',
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF0B3E75),
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            Expanded(
              child: ListView.builder(
                padding: const EdgeInsets.only(top: 8, bottom: 8),
                itemCount: _conversation.length,
                itemBuilder: (_, index) {
                  final msg = _conversation[index];
                  return ChatMessage(
                    msg.text,
                    msg.isAssistant,
                    imageUrl: msg.imageUrl,
                  );
                },
              ),
            ),
            _buildInputBar(),
          ],
        ),
      ),
    );
  }
}
