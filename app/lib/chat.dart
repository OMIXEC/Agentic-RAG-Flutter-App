import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

import 'chat_message.dart';
import 'openai.dart';
import 'pinecone.dart';

class ChatPage extends StatefulWidget {
  const ChatPage({super.key, required this.title});

  final String title;

  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage> {
  final TextEditingController _controller = TextEditingController();
  final OpenAIService _aiService = OpenAIService();
  final PineconeService _pineconeService = PineconeService();
  final List<String> _conversation = <String>[];
  bool _loading = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _fetchData(String query) async {
    final embedding = await _aiService.generateEmbeddings(query);
    if (embedding.isEmpty) {
      _appendAssistant(
        'Embedding failed. Set GOOGLE_VERTEX_ACCESS_TOKEN and GOOGLE_CLOUD_PROJECT in flutter_frontend/.env.',
      );
      return;
    }

    final pineconeResult = await _pineconeService.queryIndex(
      dotenv.env['PINECONE_INDEX'] ?? '',
      embedding,
      topK: 3,
    );

    if (pineconeResult['error'] != null) {
      _appendAssistant('Pinecone error: ${pineconeResult['error']}');
      return;
    }

    final matches = (pineconeResult['matches'] as List<dynamic>? ?? const []);
    final context = matches
        .map((match) => match['metadata']?['text'] as String? ?? '')
        .where((text) => text.isNotEmpty)
        .join('\n\n');

    final llmResponse = await _aiService.generateLLMResponse(query, context);
    _appendAssistant(llmResponse);
  }

  void _appendAssistant(String text) {
    setState(() {
      if (_conversation.isNotEmpty && _conversation.last == 'Loading...') {
        _conversation.removeLast();
      }
      _conversation.add(text);
      _loading = false;
    });
  }

  void _onSubmit() {
    final text = _controller.text.trim();
    if (text.isEmpty || _loading) {
      return;
    }

    setState(() {
      _conversation.add(text);
      _conversation.add('Loading...');
      _loading = true;
    });
    _controller.clear();
    _fetchData(text);
  }

  Widget _buildInputBar() {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 16),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
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
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _controller,
              onSubmitted: (_) => _onSubmit(),
              maxLines: null,
              decoration: const InputDecoration(
                border: InputBorder.none,
                hintText: 'Ask about your indexed docs...',
              ),
            ),
          ),
          IconButton(
            onPressed: _loading ? null : _onSubmit,
            icon: const Icon(Icons.send_rounded),
            color: const Color(0xFF1565C0),
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
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFFE3F2FD), Color(0xFFFFFFFF), Color(0xFFEAF3FF)],
          ),
        ),
        child: Column(
          children: [
            if (_conversation.isEmpty)
              const Padding(
                padding: EdgeInsets.fromLTRB(24, 32, 24, 12),
                child: Text(
                  'Ask anything about your indexed documents.',
                  style: TextStyle(
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
                itemBuilder: (context, index) => ChatMessage(
                  _conversation[index],
                  index.isOdd,
                ),
              ),
            ),
            _buildInputBar(),
          ],
        ),
      ),
    );
  }
}
