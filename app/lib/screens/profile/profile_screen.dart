/// Profile screen — user settings and app info.
library;

import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../theme/app_theme.dart';
import '../../widgets/glass_card.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final user = Supabase.instance.client.auth.currentUser;
    final email = user?.email ?? 'Not signed in';
    final displayName =
        user?.userMetadata?['display_name']?.toString() ?? 'SynapseMemo User';

    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            // Avatar + name
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(4),
              decoration: BoxDecoration(
                gradient: SynapseGradients.primaryButton,
                shape: BoxShape.circle,
              ),
              child: CircleAvatar(
                radius: 44,
                backgroundColor: SynapseColors.surfaceCard,
                child: Text(
                  displayName.isNotEmpty ? displayName[0].toUpperCase() : '?',
                  style: const TextStyle(
                    fontSize: 32,
                    fontWeight: FontWeight.w700,
                    color: SynapseColors.primary,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              displayName,
              style: const TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w700,
                color: SynapseColors.textPrimary,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              email,
              style: const TextStyle(
                fontSize: 14,
                color: SynapseColors.textSecondary,
              ),
            ),

            const SizedBox(height: 32),

            // Settings
            _SectionTitle('Preferences'),
            GlassCard(
              margin: const EdgeInsets.only(bottom: 8),
              child: _SettingsRow(
                icon: Icons.language_rounded,
                title: 'Language',
                value: 'English',
                color: SynapseColors.accent,
              ),
            ),
            GlassCard(
              margin: const EdgeInsets.only(bottom: 8),
              child: _SettingsRow(
                icon: Icons.cloud_rounded,
                title: 'Embedding Provider',
                value: 'Auto',
                color: SynapseColors.memoryKnowledge,
              ),
            ),
            GlassCard(
              margin: const EdgeInsets.only(bottom: 8),
              child: _SettingsRow(
                icon: Icons.storage_rounded,
                title: 'Storage',
                value: 'Cloud',
                color: SynapseColors.memoryEpisodic,
              ),
            ),

            const SizedBox(height: 24),
            _SectionTitle('About'),
            GlassCard(
              margin: const EdgeInsets.only(bottom: 8),
              child: _SettingsRow(
                icon: Icons.info_outline_rounded,
                title: 'Version',
                value: '1.0.0',
                color: SynapseColors.textSecondary,
              ),
            ),

            const SizedBox(height: 32),

            // Sign out
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () async {
                  await Supabase.instance.client.auth.signOut();
                },
                icon: const Icon(Icons.logout_rounded,
                    color: SynapseColors.error),
                label: const Text(
                  'Sign Out',
                  style: TextStyle(color: SynapseColors.error),
                ),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: SynapseColors.error),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final String title;

  const _SectionTitle(this.title);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 4, bottom: 8),
      child: Align(
        alignment: Alignment.centerLeft,
        child: Text(
          title,
          style: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w600,
            color: SynapseColors.textMuted,
            letterSpacing: 0.5,
          ),
        ),
      ),
    );
  }
}

class _SettingsRow extends StatelessWidget {
  final IconData icon;
  final String title;
  final String value;
  final Color color;

  const _SettingsRow({
    required this.icon,
    required this.title,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.15),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icon, color: color, size: 18),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Text(
            title,
            style: const TextStyle(
              fontSize: 15,
              color: SynapseColors.textPrimary,
            ),
          ),
        ),
        Text(
          value,
          style: const TextStyle(
            fontSize: 14,
            color: SynapseColors.textMuted,
          ),
        ),
        const SizedBox(width: 4),
        const Icon(
          Icons.chevron_right_rounded,
          color: SynapseColors.textMuted,
          size: 20,
        ),
      ],
    );
  }
}
