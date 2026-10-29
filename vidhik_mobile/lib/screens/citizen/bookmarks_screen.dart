import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../models/citizen.dart';
import '../../services/api_service.dart';
import '../../widgets/common.dart';
import '../research/research_screen.dart';

class BookmarksScreen extends StatefulWidget {
  const BookmarksScreen({super.key});

  @override
  State<BookmarksScreen> createState() => _BookmarksScreenState();
}

class _BookmarksScreenState extends State<BookmarksScreen> {
  late Future<List<BookmarkedSection>> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<ApiService>().bookmarks();
  }

  Future<void> _reload() async {
    setState(() {
      _future = context.read<ApiService>().bookmarks();
    });
    await _future;
  }

  Future<void> _remove(BookmarkedSection bookmark) async {
    final ok = await confirmDialog(
      context,
      title: 'Remove saved provision?',
      message:
          'Section ${bookmark.sectionNumber} will be removed from your saved provisions.',
      confirmLabel: 'Remove',
      destructive: true,
    );
    if (!ok) return;
    try {
      await context.read<ApiService>().removeBookmark(bookmark.sectionId);
      if (!mounted) return;
      await _reload();
      if (mounted) showInfoSnack(context, 'Saved provision removed.');
    } on Exception catch (e) {
      if (mounted) showErrorSnack(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Saved provisions'),
        actions: [
          IconButton(onPressed: _reload, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: AsyncView<List<BookmarkedSection>>(
          future: _future,
          onRetry: _reload,
          loadingText: 'Loading saved sections…',
          builder: (context, bookmarks) {
            if (bookmarks.isEmpty) {
              return EmptyState(
                title: 'No saved provisions',
                message: 'Bookmark statutory sections while researching to keep them here for quick reference.',
                icon: Icons.bookmark_border,
                action: FilledButton.icon(
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const ResearchScreen()),
                  ),
                  icon: const Icon(Icons.search),
                  label: const Text('Research provisions'),
                ),
              );
            }
            return ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 28),
              itemCount: bookmarks.length,
              separatorBuilder: (_, __) => const SizedBox(height: 9),
              itemBuilder: (context, index) {
                final item = bookmarks[index];
                return AppCard(
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => SectionDetailScreen(
                        sectionId: item.sectionId,
                        sectionNumber: item.sectionNumber,
                        lawName: item.lawName,
                      ),
                    ),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: AppColors.navy.withValues(alpha: 0.07),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          'S. ${item.sectionNumber}',
                          style: const TextStyle(
                            fontSize: 10.5,
                            fontWeight: FontWeight.w700,
                            color: AppColors.navy,
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              item.sectionTitle ?? 'Saved provision',
                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                                fontSize: 13.5,
                              ),
                            ),
                            if (item.lawName != null) ...[
                              const SizedBox(height: 2),
                              Text(
                                item.lawName!,
                                style: const TextStyle(
                                  fontSize: 11,
                                  color: AppColors.teal,
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                      IconButton(
                        tooltip: 'Remove',
                        onPressed: () => _remove(item),
                        icon: const Icon(
                          Icons.delete_outline,
                          size: 19,
                          color: AppColors.muted,
                        ),
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
