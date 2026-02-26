/// Chat screen — premium AI chat with citations.
library;

import 'package:flutter/material.dart';

import '../../models/chat_message_model.dart';
import '../../services/api_client.dart';
import '../../theme/app_theme.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> with TickerProviderStateMixin {
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final ApiClient _api = ApiClient();
  final List<ChatMessage> _messages = [];
  bool _isLoading = false;

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent + 100,
        duration: SynapseAnimations.normal,
        curve: SynapseAnimations.curve,
      );
    }
  }

  Future<void> _sendMessage() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _isLoading) return;

    _controller.clear();

    setState(() {
      _messages.add(ChatMessage(
        id: 'user-${_messages.length}',
        text: text,
        isAssistant: false,
        timestamp: DateTime.now(),
      ));
      _isLoading = true;
    });

    WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToBottom());

    try {
      final response = await _api.chatMemory(message: text);
      final answer =
          (response['answer'] ?? "I don't have enough info.").toString();
      final citations = (response['citations'] as List<dynamic>? ?? [])
          .map((c) => ChatCitation.fromJson(c as Map<String, dynamic>))
          .toList();

      if (!mounted) return;

      setState(() {
        _messages.add(ChatMessage(
          id: 'assistant-${_messages.length}',
          text: answer,
          isAssistant: true,
          citations: citations,
          timestamp: DateTime.now(),
        ));
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _messages.add(ChatMessage(
          id: 'error-${_messages.length}',
          text: 'Error: $e',
          isAssistant: true,
          timestamp: DateTime.now(),
        ));
        _isLoading = false;
      });
    }

    WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToBottom());
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Column(
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    gradient: SynapseGradients.primaryButton,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(
                    Icons.auto_awesome_rounded,
                    color: Colors.white,
                    size: 20,
                  ),
                ),
                const SizedBox(width: 12),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'SynapseMemo AI',
                      style:
                          Theme.of(context).textTheme.headlineMedium?.copyWith(
                                fontSize: 20,
                              ),
                    ),
                    const Text(
                      'Ask about your memories',
                      style: TextStyle(
                        color: SynapseColors.textMuted,
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Messages
          Expanded(
            child: _messages.isEmpty
                ? _EmptyChatState(onSuggestion: (text) {
                    _controller.text = text;
                    _sendMessage();
                  })
                : ListView.builder(
                    controller: _scrollController,
                    padding:
                        const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    itemCount: _messages.length + (_isLoading ? 1 : 0),
                    itemBuilder: (_, i) {
                      if (i == _messages.length && _isLoading) {
                        return _TypingIndicator();
                      }
                      return _ChatBubble(message: _messages[i]);
                    },
                  ),
          ),

          // Input
          _ChatInput(
            controller: _controller,
            isLoading: _isLoading,
            onSend: _sendMessage,
          ),
        ],
      ),
    );
  }
}

// ── Empty state ────────────────────────────────────────────────────────

class _EmptyChatState extends StatelessWidget {
  final void Function(String)? onSuggestion;

  const _EmptyChatState({this.onSuggestion});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                gradient: SynapseGradients.primaryButton,
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.psychology_rounded,
                size: 48,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'Your Memory Assistant',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w700,
                color: SynapseColors.textPrimary,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Ask questions about your uploaded memories.\n'
              'I can search across text, images, videos, and more.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 14,
                color: SynapseColors.textSecondary,
                height: 1.5,
              ),
            ),
            const SizedBox(height: 24),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              alignment: WrapAlignment.center,
              children: [
                _SuggestionChip('What memories do I have?',
                    onTap: onSuggestion),
                _SuggestionChip('Show me recent photos', onTap: onSuggestion),
                _SuggestionChip('What are my hobbies?', onTap: onSuggestion),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _SuggestionChip extends StatelessWidget {
  final String text;
  final void Function(String)? onTap;

  const _SuggestionChip(this.text, {this.onTap});

  @override
  Widget build(BuildContext context) {
    return ActionChip(
      label: Text(
        text,
        style: const TextStyle(
          fontSize: 12,
          color: SynapseColors.primary,
        ),
      ),
      backgroundColor: SynapseColors.primary.withValues(alpha: 0.1),
      side: BorderSide(color: SynapseColors.primary.withValues(alpha: 0.3)),
      onPressed: () => onTap?.call(text),
    );
  }
}

// ── Chat bubble ────────────────────────────────────────────────────────

class _ChatBubble extends StatelessWidget {
  final ChatMessage message;

  const _ChatBubble({required this.message});

  @override
  Widget build(BuildContext context) {
    final isAssistant = message.isAssistant;

    return Align(
      alignment: isAssistant ? Alignment.centerLeft : Alignment.centerRight,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 340),
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          gradient: isAssistant
              ? null
              : const LinearGradient(
                  colors: [SynapseColors.primary, Color(0xFF8B83FF)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
          color: isAssistant ? SynapseColors.surfaceCard : null,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(isAssistant ? 4 : 16),
            bottomRight: Radius.circular(isAssistant ? 16 : 4),
          ),
          border: isAssistant
              ? Border.all(color: SynapseColors.glassBorder, width: 0.5)
              : null,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SelectableText(
              message.text,
              style: TextStyle(
                fontSize: 14,
                height: 1.5,
                color: isAssistant ? SynapseColors.textPrimary : Colors.white,
              ),
            ),
            if (message.citations.isNotEmpty) ...[
              const SizedBox(height: 10),
              const Divider(color: SynapseColors.glassBorder, height: 1),
              const SizedBox(height: 8),
              ...message.citations.map((c) => Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.link_rounded,
                            size: 14, color: SynapseColors.accent),
                        const SizedBox(width: 6),
                        Flexible(
                          child: Text(
                            c.title,
                            style: const TextStyle(
                              fontSize: 12,
                              color: SynapseColors.accent,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  )),
            ],
          ],
        ),
      ),
    );
  }
}

// ── Typing indicator ───────────────────────────────────────────────────

class _TypingIndicator extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        decoration: BoxDecoration(
          color: SynapseColors.surfaceCard,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: SynapseColors.glassBorder, width: 0.5),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(
            3,
            (i) => Padding(
              padding: EdgeInsets.only(left: i == 0 ? 0 : 4),
              child: _Dot(delay: i * 200),
            ),
          ),
        ),
      ),
    );
  }
}

class _Dot extends StatefulWidget {
  final int delay;

  const _Dot({required this.delay});

  @override
  State<_Dot> createState() => _DotState();
}

class _DotState extends State<_Dot> with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );
    Future.delayed(Duration(milliseconds: widget.delay), () {
      if (mounted) _controller.repeat(reverse: true);
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (_, __) => Container(
        width: 8,
        height: 8,
        decoration: BoxDecoration(
          color: SynapseColors.primary
              .withValues(alpha: 0.4 + _controller.value * 0.6),
          shape: BoxShape.circle,
        ),
      ),
    );
  }
}

// ── Input bar ──────────────────────────────────────────────────────────

class _ChatInput extends StatelessWidget {
  final TextEditingController controller;
  final bool isLoading;
  final VoidCallback onSend;

  const _ChatInput({
    required this.controller,
    required this.isLoading,
    required this.onSend,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 4, 12, 12),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: SynapseColors.surfaceLight,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: SynapseColors.glassBorder, width: 0.5),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: controller,
              onSubmitted: (_) => onSend(),
              maxLines: null,
              style: const TextStyle(
                fontSize: 15,
                color: SynapseColors.textPrimary,
              ),
              decoration: const InputDecoration(
                hintText: 'Ask about your memories...',
                border: InputBorder.none,
                contentPadding: EdgeInsets.symmetric(horizontal: 4),
              ),
            ),
          ),
          const SizedBox(width: 8),
          GestureDetector(
            onTap: isLoading ? null : onSend,
            child: AnimatedContainer(
              duration: SynapseAnimations.fast,
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                gradient: isLoading ? null : SynapseGradients.primaryButton,
                color: isLoading ? SynapseColors.surfaceCard : null,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                Icons.arrow_upward_rounded,
                color: isLoading ? SynapseColors.textMuted : Colors.white,
                size: 20,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
