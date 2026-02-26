/// Home screen — tab-based navigation hub.
///
/// Contains Timeline, Search, Chat, Capture (mobile-only), Upload, and Profile tabs.
library;

import 'package:flutter/material.dart';

import '../../services/platform_utils.dart';
import '../../theme/app_theme.dart';
import '../timeline/timeline_screen.dart';
import '../search/search_screen.dart';
import '../chat/chat_screen.dart';
import '../capture/camera_capture_screen.dart';
import '../upload/upload_screen.dart';
import '../profile/profile_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with TickerProviderStateMixin {
  int _currentIndex = 0;
  late final AnimationController _fabController;

  late final List<_NavTab> _tabs;

  @override
  void initState() {
    super.initState();
    _fabController = AnimationController(
      vsync: this,
      duration: SynapseAnimations.normal,
    )..forward();

    _tabs = [
      const _NavTab(
        icon: Icons.timeline_rounded,
        label: 'Timeline',
        screen: TimelineScreen(),
      ),
      const _NavTab(
        icon: Icons.search_rounded,
        label: 'Search',
        screen: SearchScreen(),
      ),
      const _NavTab(
        icon: Icons.chat_rounded,
        label: 'Chat',
        screen: ChatScreen(),
      ),
      // Capture tab — only on mobile
      if (PlatformUtils.isMobile)
        const _NavTab(
          icon: Icons.camera_alt_rounded,
          label: 'Capture',
          screen: CameraCaptureScreen(),
          isCenter: true,
        ),
      _NavTab(
        icon: Icons.add_circle_rounded,
        label: 'Upload',
        screen: const UploadScreen(),
        isCenter: !PlatformUtils.isMobile, // center on web
      ),
      const _NavTab(
        icon: Icons.person_rounded,
        label: 'Profile',
        screen: ProfileScreen(),
      ),
    ];
  }

  @override
  void dispose() {
    _fabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: SynapseGradients.background),
        child: AnimatedSwitcher(
          duration: SynapseAnimations.normal,
          child: _tabs[_currentIndex].screen,
        ),
      ),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: SynapseColors.surface.withValues(alpha: 0.95),
          border: const Border(
            top: BorderSide(color: SynapseColors.glassBorder, width: 0.5),
          ),
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: List.generate(_tabs.length, (i) {
                final tab = _tabs[i];
                return _NavItem(
                  icon: tab.icon,
                  label: tab.label,
                  isSelected: _currentIndex == i,
                  onTap: () => setState(() => _currentIndex = i),
                  isCenter: tab.isCenter,
                );
              }),
            ),
          ),
        ),
      ),
    );
  }
}

// ── Tab data ───────────────────────────────────────────────────────────

class _NavTab {
  final IconData icon;
  final String label;
  final Widget screen;
  final bool isCenter;

  const _NavTab({
    required this.icon,
    required this.label,
    required this.screen,
    this.isCenter = false,
  });
}

// ── Nav item ───────────────────────────────────────────────────────────

class _NavItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool isSelected;
  final VoidCallback onTap;
  final bool isCenter;

  const _NavItem({
    required this.icon,
    required this.label,
    required this.isSelected,
    required this.onTap,
    this.isCenter = false,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: AnimatedContainer(
        duration: SynapseAnimations.fast,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: isCenter && isSelected
            ? BoxDecoration(
                gradient: SynapseGradients.primaryButton,
                borderRadius: BorderRadius.circular(20),
              )
            : null,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: isCenter ? 28 : 24,
              color: isSelected
                  ? (isCenter ? Colors.white : SynapseColors.primary)
                  : SynapseColors.textMuted,
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: 10,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                color: isSelected
                    ? (isCenter ? Colors.white : SynapseColors.primary)
                    : SynapseColors.textMuted,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
