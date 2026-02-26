import 'package:flutter/material.dart';

class ChatMessage extends StatelessWidget {
  final String text;
  final bool isAssistant;
  final String? imageUrl;

  const ChatMessage(
    this.text,
    this.isAssistant, {
    this.imageUrl,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    final bubble = BoxDecoration(
      gradient: isAssistant
          ? const LinearGradient(
              colors: [Color(0xFFEAF4FF), Color(0xFFDDEBFF)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            )
          : const LinearGradient(
              colors: [Color(0xFF1976D2), Color(0xFF42A5F5)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
      borderRadius: BorderRadius.circular(18),
      border: Border.all(color: const Color(0x332196F3)),
      boxShadow: const [
        BoxShadow(
          color: Color(0x14000000),
          blurRadius: 10,
          offset: Offset(0, 4),
        ),
      ],
    );

    return Align(
      alignment: isAssistant ? Alignment.centerLeft : Alignment.centerRight,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 760),
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: bubble,
        child: Column(
          crossAxisAlignment:
              isAssistant ? CrossAxisAlignment.start : CrossAxisAlignment.end,
          children: [
            if ((imageUrl ?? '').isNotEmpty)
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.network(
                  imageUrl!,
                  height: 150,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => Container(
                    height: 70,
                    width: 220,
                    color: Colors.white24,
                    alignment: Alignment.center,
                    child: Text(
                      'Image preview unavailable',
                      style: TextStyle(
                        color: isAssistant ? const Color(0xFF0F2E4F) : Colors.white,
                      ),
                    ),
                  ),
                ),
              ),
            if ((imageUrl ?? '').isNotEmpty) const SizedBox(height: 8),
            Text(
              text,
              style: TextStyle(
                fontSize: 15,
                height: 1.35,
                color: isAssistant ? const Color(0xFF0F2E4F) : Colors.white,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
