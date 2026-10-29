import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/auth_provider.dart';
import 'admin/admin_screen.dart';
import 'assistant/assistant_screen.dart';
import 'cases/citizen_cases_screen.dart';
import 'dashboard/citizen_dashboard_screen.dart';
import 'lawyer/lawyer_workspace_screen.dart';
import 'more_screen.dart';
import 'research/research_screen.dart';

/// Primary navigation shell. The destination set follows the authenticated
/// role returned by `/api/auth/me` so citizens, advocates and administrators
/// each land on the workspace that exists for them.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;

  void _goTo(int index) {
    if (!mounted) return;
    setState(() {
      _index = index;
    });
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final isLawyer = auth.user?.isLawyer ?? false;
    final isAdmin = auth.user?.isAdmin ?? false;

    final destinations = <_Destination>[
      if (isAdmin)
        _Destination(
          label: 'Admin',
          icon: Icons.admin_panel_settings_outlined,
          selectedIcon: Icons.admin_panel_settings,
          screen: const AdminScreen(),
        )
      else if (isLawyer)
        _Destination(
          label: 'Workspace',
          icon: Icons.work_outline,
          selectedIcon: Icons.work,
          screen: const LawyerWorkspaceScreen(),
        )
      else
        _Destination(
          label: 'Home',
          icon: Icons.home_outlined,
          selectedIcon: Icons.home,
          screen: CitizenDashboardScreen(
            onNavigateTab: (target) {
              // Dashboard shortcuts: 1 = assistant, 2 = cases, 3 = research.
              if (target >= 0 && target < 4) _goTo(target);
            },
          ),
        ),
      _Destination(
        label: 'Assistant',
        icon: Icons.smart_toy_outlined,
        selectedIcon: Icons.smart_toy,
        screen: const AssistantScreen(),
      ),
      if (isLawyer || !isAdmin)
        _Destination(
          label: isLawyer ? 'Research' : 'Cases',
          icon: isLawyer ? Icons.search : Icons.folder_outlined,
          selectedIcon: isLawyer ? Icons.search : Icons.folder,
          screen: isLawyer
              ? const ResearchScreen()
              : const CitizenCasesScreen(),
        ),
      if (!isLawyer && !isAdmin)
        _Destination(
          label: 'Research',
          icon: Icons.menu_book_outlined,
          selectedIcon: Icons.menu_book,
          screen: const ResearchScreen(),
        ),
      const _Destination(
        label: 'More',
        icon: Icons.grid_view_outlined,
        selectedIcon: Icons.grid_view,
        screen: MoreScreen(),
      ),
    ];

    if (_index >= destinations.length) _index = 0;

    return Scaffold(
      body: IndexedStack(
        index: _index,
        children: [
          for (var i = 0; i < destinations.length; i++)
            _KeepAlive(child: destinations[i].screen),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: _goTo,
        destinations: [
          for (final destination in destinations)
            NavigationDestination(
              icon: Icon(destination.icon),
              selectedIcon: Icon(destination.selectedIcon),
              label: destination.label,
            ),
        ],
      ),
    );
  }
}

class _Destination {
  const _Destination({
    required this.label,
    required this.icon,
    required this.selectedIcon,
    required this.screen,
  });

  final String label;
  final IconData icon;
  final IconData selectedIcon;
  final Widget screen;
}

/// Keeps tab state (scroll offset, form input) alive while switching tabs.
class _KeepAlive extends StatefulWidget {
  const _KeepAlive({required this.child});

  final Widget child;

  @override
  State<_KeepAlive> createState() => _KeepAliveState();
}

class _KeepAliveState extends State<_KeepAlive>
    with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return widget.child;
  }
}
