import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/format.dart';
import '../../models/legal.dart';
import '../../services/api_service.dart';
import '../../widgets/common.dart';

class ResearchScreen extends StatefulWidget {
  const ResearchScreen({super.key, this.initialQuery});

  final String? initialQuery;

  @override
  State<ResearchScreen> createState() => _ResearchScreenState();
}

class _ResearchScreenState extends State<ResearchScreen> {
  final _queryController = TextEditingController();
  final _scrollController = ScrollController();

  List<LegalSearchResult> _results = [];
  int _total = 0;
  int _offset = 0;
  bool _loading = false;
  bool _loadingMore = false;
  String? _error;
  String _lastQuery = '';

  List<LawAct> _acts = [];
  int? _lawFilter;

  static const _pageSize = 20;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    _loadActs();
    if (widget.initialQuery != null && widget.initialQuery!.trim().isNotEmpty) {
      _queryController.text = widget.initialQuery!;
      _search();
    }
  }

  @override
  void dispose() {
    _queryController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadActs() async {
    try {
      final acts = await context.read<ApiService>().acts();
      if (!mounted) return;
      setState(() {
        _acts = acts;
      });
    } catch (_) {
      // Filter is optional; search still works without it.
    }
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 240) {
      _loadMore();
    }
  }

  Future<void> _search() async {
    final query = _queryController.text.trim();
    if (query.isEmpty) {
      setState(() {
        _error = 'Enter a legal term, section number or phrase.';
      });
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
      _results = [];
      _offset = 0;
      _lastQuery = query;
    });
    try {
      final page = await context.read<ApiService>().search(
        query,
        limit: _pageSize,
        offset: 0,
        lawId: _lawFilter,
      );
      if (!mounted) return;
      setState(() {
        _results = page.results;
        _total = page.total;
        _offset = page.results.length;
      });
      _recordHistory(query, page.total);
    } on Exception catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e'.replaceFirst('ApiException: ', '');
      });
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  Future<void> _recordHistory(String query, int results) async {
    try {
      await context.read<ApiService>().recordSearch(query, results);
    } catch (_) {
      // Search history is a convenience; ignore failures for guest sessions.
    }
  }

  Future<void> _loadMore() async {
    if (_loadingMore || _loading || _results.length >= _total) return;
    setState(() {
      _loadingMore = true;
    });
    try {
      final page = await context.read<ApiService>().search(
        _lastQuery,
        limit: _pageSize,
        offset: _offset,
        lawId: _lawFilter,
      );
      if (!mounted) return;
      setState(() {
        _results = [..._results, ...page.results];
        _offset = _results.length;
        _total = page.total;
      });
    } catch (_) {
      // Keep the existing page visible on pagination failure.
    } finally {
      if (mounted) {
        setState(() {
          _loadingMore = false;
        });
      }
    }
  }

  void _clear() {
    _queryController.clear();
    setState(() {
      _results = [];
      _total = 0;
      _offset = 0;
      _error = null;
      _lastQuery = '';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Legal research'),
        actions: [
          IconButton(
            tooltip: 'Clear',
            onPressed: _clear,
            icon: const Icon(Icons.clear_all),
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
            child: Column(
              children: [
                TextField(
                  controller: _queryController,
                  textInputAction: TextInputAction.search,
                  onSubmitted: (_) => _search(),
                  decoration: InputDecoration(
                    hintText: 'Search sections, offences, rights, phrases…',
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: IconButton(
                      onPressed: _loading ? null : _search,
                      icon: const Icon(Icons.arrow_forward),
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: DropdownButtonFormField<int?>(
                        initialValue: _lawFilter,
                        isExpanded: true,
                        decoration: const InputDecoration(
                          labelText: 'Statute filter',
                          isDense: true,
                          contentPadding: EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 10,
                          ),
                        ),
                        items: [
                          const DropdownMenuItem<int?>(
                            value: null,
                            child: Text('All statutes'),
                          ),
                          for (final act in _acts)
                            DropdownMenuItem<int?>(
                              value: act.actId,
                              child: Text(
                                '${act.shortName} · ${act.year}',
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                        ],
                        onChanged: (value) {
                          setState(() {
                            _lawFilter = value;
                          });
                          if (_lastQuery.isNotEmpty) _search();
                        },
                      ),
                    ),
                    const SizedBox(width: 10),
                    FilledButton(
                      onPressed: _loading ? null : _search,
                      child: _loading
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : const Text('Search'),
                    ),
                  ],
                ),
              ],
            ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              child: Text(
                _error!,
                style: const TextStyle(color: AppColors.danger, fontSize: 12),
              ),
            ),
          if (_lastQuery.isNotEmpty && !_loading)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      '$_total result${_total == 1 ? '' : 's'} for "$_lastQuery"',
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppColors.muted,
                      ),
                    ),
                  ),
                  if (_total > 0)
                    Text(
                      'Showing ${_results.length}',
                      style: const TextStyle(
                        fontSize: 11,
                        color: AppColors.muted,
                      ),
                    ),
                ],
              ),
            ),
          Expanded(
            child: _loading
                ? const Center(
                    child: CircularProgressIndicator(strokeWidth: 2.4),
                  )
                : _results.isEmpty
                ? EmptyState(
                    title: _lastQuery.isEmpty
                        ? 'Search Indian statutory law'
                        : 'No matching provisions',
                    message: _lastQuery.isEmpty
                        ? 'Search BNS, BNSS, BSA, the Constitution and 24 central Acts by keyword, section number or legal phrase.'
                        : 'Try broader terms or remove the statute filter.',
                    icon: Icons.menu_book_outlined,
                  )
                : ListView.separated(
                    controller: _scrollController,
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                    itemCount: _results.length + (_loadingMore ? 1 : 0),
                    separatorBuilder: (_, __) => const SizedBox(height: 9),
                    itemBuilder: (context, index) {
                      if (index >= _results.length) {
                        return const Padding(
                          padding: EdgeInsets.all(16),
                          child: Center(
                            child: SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            ),
                          ),
                        );
                      }
                      return _resultCard(_results[index]);
                    },
                  ),
          ),
        ],
      ),
    );
  }

  Widget _resultCard(LegalSearchResult result) {
    return AppCard(
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => SectionDetailScreen(
            sectionId: result.sectionId,
            sectionNumber: result.sectionNumber,
            lawName: result.lawName,
          ),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AppColors.navy.withValues(alpha: 0.07),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  'Section ${result.sectionNumber}',
                  style: const TextStyle(
                    fontSize: 10.5,
                    fontWeight: FontWeight.w700,
                    color: AppColors.navy,
                  ),
                ),
              ),
              const Spacer(),
              if (result.jurisdiction != null)
                Text(
                  result.jurisdiction!,
                  style: const TextStyle(fontSize: 10, color: AppColors.muted),
                ),
            ],
          ),
          const SizedBox(height: 7),
          Text(
            result.sectionTitle ?? 'Untitled provision',
            style: const TextStyle(
              fontWeight: FontWeight.w600,
              fontSize: 14,
              height: 1.3,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            result.lawName,
            style: const TextStyle(fontSize: 11, color: AppColors.teal),
          ),
          if (result.snippet != null) ...[
            const SizedBox(height: 8),
            Text(
              cleanLegalText(result.snippet),
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontSize: 12,
                color: AppColors.muted,
                height: 1.45,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class SectionDetailScreen extends StatefulWidget {
  const SectionDetailScreen({
    super.key,
    required this.sectionId,
    required this.sectionNumber,
    this.lawName,
  });

  final int sectionId;
  final String sectionNumber;
  final String? lawName;

  @override
  State<SectionDetailScreen> createState() => _SectionDetailScreenState();
}

class _SectionDetailScreenState extends State<SectionDetailScreen> {
  late Future<StatuteSection> _future;
  bool _bookmarkBusy = false;
  bool? _bookmarked;

  @override
  void initState() {
    super.initState();
    _future = context.read<ApiService>().section(widget.sectionId);
    _loadBookmarkState();
  }

  Future<void> _loadBookmarkState() async {
    try {
      final bookmarks = await context.read<ApiService>().bookmarks();
      if (!mounted) return;
      setState(() {
        _bookmarked = bookmarks.any((b) => b.sectionId == widget.sectionId);
      });
    } catch (_) {
      // Guest session or backend unavailable: hide the toggle.
    }
  }

  Future<void> _toggleBookmark() async {
    final api = context.read<ApiService>();
    setState(() {
      _bookmarkBusy = true;
    });
    try {
      if (_bookmarked == true) {
        await api.removeBookmark(widget.sectionId);
        if (mounted) {
          setState(() {
            _bookmarked = false;
          });
          showInfoSnack(context, 'Removed from saved provisions.');
        }
      } else {
        await api.addBookmark(widget.sectionId);
        if (mounted) {
          setState(() {
            _bookmarked = true;
          });
          showInfoSnack(context, 'Saved to your provisions.');
        }
      }
    } on Exception catch (e) {
      if (mounted) showErrorSnack(context, e);
    } finally {
      if (mounted) {
        setState(() {
          _bookmarkBusy = false;
        });
      }
    }
  }

  Future<void> _openKnowledgeContext(StatuteSection section) async {
    try {
      final api = context.read<ApiService>();
      final acts = await api.acts();
      if (!mounted) return;
      final match = acts.where((a) => a.actId == section.lawId).toList();
      final code = match.isEmpty ? null : match.first.shortName;
      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => SectionKnowledgeScreen(
            sectionNumber: section.sectionNumber,
            lawCode: code,
          ),
        ),
      );
    } on Exception catch (e) {
      if (mounted) showErrorSnack(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Section ${widget.sectionNumber}'),
        actions: [
          if (_bookmarked != null)
            IconButton(
              tooltip: _bookmarked == true
                  ? 'Remove bookmark'
                  : 'Save provision',
              onPressed: _bookmarkBusy ? null : _toggleBookmark,
              icon: Icon(
                _bookmarked == true ? Icons.bookmark : Icons.bookmark_border,
              ),
            ),
        ],
      ),
      body: AsyncView<StatuteSection>(
        future: _future,
        onRetry: () => setState(() {
          _future = context.read<ApiService>().section(widget.sectionId);
        }),
        loadingText: 'Loading statutory text…',
        builder: (context, section) {
          final text = section.text;
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 30),
            children: [
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Section ${section.sectionNumber}',
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: AppColors.teal,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      section.sectionTitle ?? 'Statutory provision',
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                        height: 1.3,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      widget.lawName ?? 'Act #${section.lawId}',
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppColors.muted,
                      ),
                    ),
                    if (section.chapter != null &&
                        section.chapter!.isNotEmpty) ...[
                      const SizedBox(height: 6),
                      Wrap(
                        spacing: 6,
                        children: [
                          Tag(section.chapter!),
                          if (section.jurisdiction != null)
                            Tag(section.jurisdiction!),
                          if (section.isOmitted)
                            const Tag('Omitted', color: AppColors.danger),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 14),
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Text(
                          'Statutory text',
                          style: TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 13.5,
                          ),
                        ),
                        const Spacer(),
                        IconButton(
                          tooltip: 'Copy text',
                          onPressed: text.isEmpty
                              ? null
                              : () {
                                  Clipboard.setData(ClipboardData(text: text));
                                  showInfoSnack(
                                    context,
                                    'Section text copied.',
                                  );
                                },
                          icon: const Icon(Icons.copy, size: 18),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    SelectableText(
                      text.isEmpty
                          ? 'No text available for this section.'
                          : text,
                      style: const TextStyle(fontSize: 13.5, height: 1.6),
                    ),
                    if (section.isOmitted && section.omissionNote != null) ...[
                      const SizedBox(height: 10),
                      Text(
                        section.omissionNote!,
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.danger,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 14),
              if (section.sourcePdf != null || section.pageStart != null)
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Source provenance',
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 13,
                        ),
                      ),
                      const SizedBox(height: 8),
                      InfoRow('Document', section.sourcePdf ?? '—'),
                      InfoRow(
                        'Pages',
                        section.pageStart == null
                            ? '—'
                            : '${section.pageStart}'
                                  '${section.pageEnd != null ? '–${section.pageEnd}' : ''}',
                      ),
                      InfoRow('Jurisdiction', section.jurisdiction ?? '—'),
                    ],
                  ),
                ),
              const SizedBox(height: 14),
              OutlinedButton.icon(
                onPressed: () => _openKnowledgeContext(section),
                icon: const Icon(Icons.account_tree_outlined),
                label: const Text('Related offences, procedure & judgments'),
              ),
              const SizedBox(height: 10),
              Text(
                'Statutory text is reproduced from official sources in the Vidhik database. Verify against the Gazette before filing.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 10.5,
                  color: AppColors.muted,
                  height: 1.4,
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class SectionKnowledgeScreen extends StatefulWidget {
  const SectionKnowledgeScreen({
    super.key,
    required this.sectionNumber,
    this.lawCode,
  });

  final String sectionNumber;
  final String? lawCode;

  @override
  State<SectionKnowledgeScreen> createState() => _SectionKnowledgeScreenState();
}

class _SectionKnowledgeScreenState extends State<SectionKnowledgeScreen> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<ApiService>().sectionContext(
      widget.sectionNumber,
      lawCode: widget.lawCode,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Section ${widget.sectionNumber} context')),
      body: AsyncView<Map<String, dynamic>>(
        future: _future,
        onRetry: () => setState(() {
          _future = context.read<ApiService>().sectionContext(
            widget.sectionNumber,
            lawCode: widget.lawCode,
          );
        }),
        loadingText: 'Loading related knowledge…',
        builder: (context, data) {
          final offence = asMap(data['offence']);
          final punishment = asMap(data['punishment']);
          final procedures = asMapList(data['procedures']);
          final evidence = asMapList(data['evidence_provisions']);
          final predecessors = asMapList(data['predecessor_mappings']);
          final judgments = asMapList(data['judgments']);

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      firstNonEmpty([data['law_name'], 'Statute']),
                      style: const TextStyle(
                        fontSize: 13,
                        color: AppColors.teal,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Section ${firstNonEmpty([data['section_number'], widget.sectionNumber])} — '
                      '${firstNonEmpty([data['section_title'], ''])}',
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    if (asString(data['full_text']).isNotEmpty) ...[
                      const SizedBox(height: 10),
                      Text(
                        cleanLegalText(data['full_text']),
                        style: const TextStyle(fontSize: 12.5, height: 1.55),
                      ),
                    ],
                  ],
                ),
              ),
              if (offence.isNotEmpty) ...[
                const SizedBox(height: 14),
                const SectionTitle('Offence'),
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      InfoRow(
                        'Offence',
                        firstNonEmpty([offence['offence_name'], '—']),
                      ),
                      InfoRow(
                        'Nature',
                        firstNonEmpty([offence['offence_type'], '—']),
                      ),
                      InfoRow(
                        'Cognizance',
                        firstNonEmpty([offence['cognizable'], '—']),
                      ),
                      InfoRow(
                        'Bailability',
                        firstNonEmpty([offence['bailable'], '—']),
                      ),
                      InfoRow(
                        'Triable by',
                        firstNonEmpty([offence['triable_by'], '—']),
                      ),
                    ],
                  ),
                ),
              ],
              if (punishment.isNotEmpty) ...[
                const SizedBox(height: 14),
                const SectionTitle('Punishment'),
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      InfoRow(
                        'Imprisonment',
                        firstNonEmpty([punishment['imprisonment'], '—']),
                      ),
                      InfoRow('Fine', firstNonEmpty([punishment['fine'], '—'])),
                      if (asString(punishment['description']).isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(top: 6),
                          child: Text(
                            asString(punishment['description']),
                            style: const TextStyle(fontSize: 12.5, height: 1.4),
                          ),
                        ),
                    ],
                  ),
                ),
              ],
              if (procedures.isNotEmpty) ...[
                const SizedBox(height: 14),
                const SectionTitle('Procedure'),
                for (final procedure in procedures)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: AppCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            firstNonEmpty([
                              procedure['procedure_name'],
                              'Procedure',
                            ]),
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            asString(procedure['description']),
                            style: const TextStyle(fontSize: 12.5, height: 1.4),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
              if (evidence.isNotEmpty) ...[
                const SizedBox(height: 14),
                const SectionTitle('Evidence provisions'),
                for (final item in evidence)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: AppCard(
                      child: Text(
                        firstNonEmpty([
                          item['description'],
                          item['evidence_name'],
                          'Evidence provision',
                        ]),
                        style: const TextStyle(fontSize: 12.5, height: 1.4),
                      ),
                    ),
                  ),
              ],
              if (predecessors.isNotEmpty) ...[
                const SizedBox(height: 14),
                const SectionTitle('Predecessor mapping'),
                for (final item in predecessors)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: AppCard(
                      child: Text(
                        '${firstNonEmpty([item['old_act_name'], 'Old Act'])} '
                        '${firstNonEmpty([item['old_section_number'], ''])} → '
                        '${firstNonEmpty([item['new_section_number'], widget.sectionNumber])}',
                        style: const TextStyle(fontSize: 12.5),
                      ),
                    ),
                  ),
              ],
              if (judgments.isNotEmpty) ...[
                const SizedBox(height: 14),
                const SectionTitle('Verified judgments'),
                for (final judgment in judgments)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: AppCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            firstNonEmpty([judgment['case_title'], 'Judgment']),
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            [
                              firstNonEmpty([judgment['court'], '']),
                              firstNonEmpty([judgment['year'], '']),
                              firstNonEmpty([judgment['citation'], '']),
                            ].where((e) => e.isNotEmpty).join(' · '),
                            style: const TextStyle(
                              fontSize: 11,
                              color: AppColors.muted,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
              if (offence.isEmpty &&
                  punishment.isEmpty &&
                  procedures.isEmpty &&
                  evidence.isEmpty &&
                  predecessors.isEmpty &&
                  judgments.isEmpty)
                const Padding(
                  padding: EdgeInsets.only(top: 20),
                  child: EmptyState(
                    title: 'No linked knowledge records',
                    message: 'This section has statutory text but no additional offence, procedure or judgment records in the knowledge base.',
                    icon: Icons.info_outline,
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}
