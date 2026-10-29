import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/format.dart';
import '../../models/citizen.dart';
import '../../services/api_service.dart';
import '../../widgets/common.dart';
import '../research/research_screen.dart';

class SearchHistoryScreen extends StatefulWidget {
  const SearchHistoryScreen({super.key});

  @override
  State<SearchHistoryScreen> createState() => _SearchHistoryScreenState();
}

class _SearchHistoryScreenState extends State<SearchHistoryScreen> {
  late Future<List<SearchHistoryEntry>> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<ApiService>().searchHistory();
  }

  Future<void> _reload() async {
    setState(() {
      _future = context.read<ApiService>().searchHistory();
    });
    await _future;
  }

  Future<void> _clear() async {
    final ok = await confirmDialog(
      context,
      title: 'Clear search history?',
      message: 'All stored legal research queries will be permanently removed.',
      confirmLabel: 'Clear history',
      destructive: true,
    );
    if (!ok) return;
    try {
      await context.read<ApiService>().clearSearchHistory();
      if (!mounted) return;
      await _reload();
      if (mounted) showInfoSnack(context, 'Search history cleared.');
    } on Exception catch (e) {
      if (mounted) showErrorSnack(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Search history'),
        actions: [
          IconButton(
            tooltip: 'Clear history',
            onPressed: _clear,
            icon: const Icon(Icons.delete_sweep_outlined),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: AsyncView<List<SearchHistoryEntry>>(
          future: _future,
          onRetry: _reload,
          loadingText: 'Loading search history…',
          builder: (context, entries) {
            if (entries.isEmpty) {
              return const EmptyState(
                title: 'No search history',
                message: 'Your legal research queries will be listed here.',
                icon: Icons.history,
              );
            }
            return ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 28),
              itemCount: entries.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (context, index) {
                final entry = entries[index];
                return AppCard(
                  onTap: entry.queryText.isEmpty
                      ? null
                      : () => Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) =>
                                ResearchScreen(initialQuery: entry.queryText),
                          ),
                        ),
                  child: Row(
                    children: [
                      const Icon(Icons.search, size: 18, color: AppColors.teal),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              entry.queryText,
                              style: const TextStyle(
                                fontWeight: FontWeight.w500,
                                fontSize: 13.5,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              [
                                if (entry.resultsCount != null)
                                  '${entry.resultsCount} results',
                                if (asString(entry.createdAt).isNotEmpty)
                                  formatDateTime(entry.createdAt),
                              ].join(' · '),
                              style: const TextStyle(
                                fontSize: 10.5,
                                color: AppColors.muted,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const Icon(
                        Icons.north_east,
                        size: 16,
                        color: AppColors.muted,
                      ),
                    ],
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}
