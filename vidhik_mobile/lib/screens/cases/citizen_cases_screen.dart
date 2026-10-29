import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/format.dart';
import '../../models/citizen.dart';
import '../../services/api_service.dart';
import '../../widgets/common.dart';
import '../courts/case_tracking_screen.dart';
import 'case_intelligence_screen.dart';

class CitizenCasesScreen extends StatefulWidget {
  const CitizenCasesScreen({super.key});

  @override
  State<CitizenCasesScreen> createState() => _CitizenCasesScreenState();
}

class _CitizenCasesScreenState extends State<CitizenCasesScreen> {
  late Future<List<CitizenCase>> _future;
  String _filter = '';

  @override
  void initState() {
    super.initState();
    _future = context.read<ApiService>().citizenCases();
  }

  Future<void> _reload() async {
    setState(() {
      _future = context.read<ApiService>().citizenCases();
    });
    await _future;
  }

  Future<void> _openCreate() async {
    final created = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const _CreateCaseSheet(),
    );
    if (created == true) _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('My legal matters'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _reload,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openCreate,
        backgroundColor: AppColors.teal,
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add),
        label: const Text('New case'),
      ),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 6),
              child: TextField(
                onChanged: (value) =>
                    setState(() => _filter = value.toLowerCase()),
                decoration: const InputDecoration(
                  hintText: 'Filter by title, court or status',
                  prefixIcon: Icon(Icons.search),
                  isDense: true,
                ),
              ),
            ),
            Expanded(
              child: AsyncView<List<CitizenCase>>(
                future: _future,
                onRetry: _reload,
                loadingText: 'Loading your cases…',
                builder: (context, cases) {
                  final filtered = _filter.isEmpty
                      ? cases
                      : cases
                            .where(
                              (c) => [
                                c.title,
                                c.caseNumber ?? '',
                                c.courtName ?? '',
                                c.status,
                                c.caseType ?? '',
                              ].join(' ').toLowerCase().contains(_filter),
                            )
                            .toList();
                  if (filtered.isEmpty) {
                    return EmptyState(
                      title: _filter.isEmpty
                          ? 'No cases registered'
                          : 'No matching cases',
                      message: _filter.isEmpty
                          ? 'Register a matter to track hearings, documents and court references.'
                          : 'Try a different title, court or status.',
                      icon: Icons.folder_open_outlined,
                      action: _filter.isEmpty
                          ? FilledButton.icon(
                              onPressed: _openCreate,
                              icon: const Icon(Icons.add),
                              label: const Text('Register a case'),
                            )
                          : null,
                    );
                  }
                  return ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 90),
                    itemCount: filtered.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 10),
                    itemBuilder: (context, index) => _caseCard(filtered[index]),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _caseCard(CitizenCase item) {
    final statusColor = switch (item.status.toLowerCase()) {
      'active' => AppColors.teal,
      'pending' => AppColors.warning,
      'resolved' || 'closed' => AppColors.success,
      'withdrawn' => AppColors.muted,
      _ => AppColors.navy,
    };
    return AppCard(
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => CitizenCaseDetailScreen(caseId: item.caseId),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  item.title,
                  style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 15,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Tag(item.status.toUpperCase(), color: statusColor),
            ],
          ),
          if (item.caseNumber != null || item.caseType != null) ...[
            const SizedBox(height: 4),
            Text(
              [
                if (item.caseNumber != null) 'No. ${item.caseNumber}',
                if (item.caseType != null) item.caseType!,
              ].join(' · '),
              style: const TextStyle(fontSize: 11.5, color: AppColors.muted),
            ),
          ],
          if (item.courtName != null) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                const Icon(
                  Icons.account_balance_outlined,
                  size: 14,
                  color: AppColors.muted,
                ),
                const SizedBox(width: 5),
                Expanded(
                  child: Text(
                    item.courtName!,
                    style: const TextStyle(fontSize: 12),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ],
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 6,
            children: [
              Tag('${item.documentsCount} docs', color: AppColors.info),
              Tag('${item.hearingsCount} hearings', color: AppColors.accent),
              if (item.cnrNumber != null)
                Tag('CNR ${item.cnrNumber}', color: AppColors.success),
            ],
          ),
        ],
      ),
    );
  }
}

class CitizenCaseDetailScreen extends StatefulWidget {
  const CitizenCaseDetailScreen({super.key, required this.caseId});

  final int caseId;

  @override
  State<CitizenCaseDetailScreen> createState() =>
      _CitizenCaseDetailScreenState();
}

class _CitizenCaseDetailScreenState extends State<CitizenCaseDetailScreen> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<ApiService>().citizenCaseRaw(widget.caseId);
  }

  Future<void> _reload() async {
    setState(() {
      _future = context.read<ApiService>().citizenCaseRaw(widget.caseId);
    });
    await _future;
  }

  Future<void> _editCourtReference() async {
    final changed = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) =>
          _CourtReferenceSheet(caseId: widget.caseId, initial: _future),
    );
    if (changed == true) _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Case details'),
        actions: [
          IconButton(
            tooltip: 'Track on eCourts',
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => CaseTrackingScreen(caseId: widget.caseId),
              ),
            ),
            icon: const Icon(Icons.track_changes),
          ),
        ],
      ),
      body: AsyncView<Map<String, dynamic>>(
        future: _future,
        onRetry: _reload,
        loadingText: 'Loading case record…',
        builder: (context, data) {
          final item = CitizenCase.fromJson(data);
          final documents = asMapList(data['documents']);
          final hearings = asMapList(data['hearings']);
          final sections = asMapList(data['legal_sections']);
          final lawyer = asMap(data['lawyer']);

          return RefreshIndicator(
            onRefresh: _reload,
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 30),
              children: [
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              item.title,
                              style: const TextStyle(
                                fontSize: 17,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                          Tag(item.status.toUpperCase()),
                        ],
                      ),
                      const SizedBox(height: 10),
                      InfoRow('Case number', item.caseNumber ?? '—'),
                      InfoRow('Type', item.caseType ?? '—'),
                      InfoRow('Court', item.courtName ?? '—'),
                      InfoRow('Opposite party', item.oppositeParty ?? '—'),
                      InfoRow('Filed on', formatDate(item.createdAt)),
                      InfoRow('Location', item.location ?? '—'),
                      InfoRow('Police station', item.policeStation ?? '—'),
                      InfoRow(
                        'Assigned lawyer',
                        item.assignedLawyerName ?? 'Unassigned',
                      ),
                      if (asString(lawyer['phone']).isNotEmpty)
                        InfoRow('Lawyer phone', asString(lawyer['phone'])),
                    ],
                  ),
                ),
                if ((item.description ?? '').isNotEmpty) ...[
                  const SizedBox(height: 14),
                  const SectionTitle('Case description'),
                  AppCard(
                    child: Text(
                      cleanLegalText(item.description),
                      style: const TextStyle(fontSize: 13, height: 1.55),
                    ),
                  ),
                ],
                const SizedBox(height: 14),
                const SectionTitle('Court reference (eCourts)'),
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      InfoRow('CNR number', item.cnrNumber ?? 'Not linked'),
                      InfoRow(
                        'Source',
                        asString(data['court_source'], 'eCourts India'),
                      ),
                      InfoRow('Court status', item.externalStatus ?? '—'),
                      InfoRow('Next hearing', formatDate(item.nextHearingDate)),
                      InfoRow(
                        'Last verified',
                        formatDateTime(data['last_verified_at']),
                      ),
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: _editCourtReference,
                              icon: const Icon(Icons.edit_outlined, size: 17),
                              label: const Text('Update reference'),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: FilledButton.icon(
                              onPressed: () => Navigator.of(context).push(
                                MaterialPageRoute(
                                  builder: (_) =>
                                      CaseTrackingScreen(caseId: widget.caseId),
                                ),
                              ),
                              icon: const Icon(Icons.track_changes, size: 17),
                              label: const Text('Track'),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 14),
                SectionTitle('Hearings (${hearings.length})'),
                if (hearings.isEmpty)
                  const AppCard(
                    child: Text(
                      'No hearings scheduled for this matter.',
                      style: TextStyle(color: AppColors.muted),
                    ),
                  )
                else
                  for (final hearing in hearings)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: AppCard(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              firstNonEmpty([hearing['purpose'], 'Hearing']),
                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              [
                                formatDate(hearing['hearing_date']),
                                if (asString(hearing['courtroom']).isNotEmpty)
                                  'Courtroom ${hearing['courtroom']}',
                                if (asString(hearing['status']).isNotEmpty)
                                  asString(hearing['status']),
                              ].join(' · '),
                              style: const TextStyle(
                                fontSize: 12,
                                color: AppColors.muted,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                const SizedBox(height: 14),
                SectionTitle('Documents (${documents.length})'),
                if (documents.isEmpty)
                  const AppCard(
                    child: Text(
                      'No documents uploaded for this matter.',
                      style: TextStyle(color: AppColors.muted),
                    ),
                  )
                else
                  for (final doc in documents)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: AppCard(
                        child: Row(
                          children: [
                            const Icon(
                              Icons.description_outlined,
                              size: 18,
                              color: AppColors.teal,
                            ),
                            const SizedBox(width: 9),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    firstNonEmpty([
                                      doc['document_name'],
                                      'Document',
                                    ]),
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w600,
                                      fontSize: 13,
                                    ),
                                  ),
                                  Text(
                                    '${firstNonEmpty([doc['document_type'], 'General'])} · ${firstNonEmpty([doc['upload_status'], 'uploaded'])}',
                                    style: const TextStyle(
                                      fontSize: 11.5,
                                      color: AppColors.muted,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                if (sections.isNotEmpty) ...[
                  const SizedBox(height: 14),
                  SectionTitle('Linked statutory sections'),
                  for (final section in sections)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: AppCard(
                        child: Text(
                          '${firstNonEmpty([section['law_name'], 'Act'])} — Section ${firstNonEmpty([section['section_number'], '—'])}'
                          '${asString(section['section_title']).isNotEmpty ? ': ${section['section_title']}' : ''}',
                          style: const TextStyle(fontSize: 12.5, height: 1.4),
                        ),
                      ),
                    ),
                ],
                const SizedBox(height: 18),
                FilledButton.icon(
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) =>
                          CaseIntelligenceScreen(caseId: widget.caseId),
                    ),
                  ),
                  icon: const Icon(Icons.psychology_alt_outlined),
                  label: const Text('Open case intelligence'),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _CreateCaseSheet extends StatefulWidget {
  const _CreateCaseSheet();

  @override
  State<_CreateCaseSheet> createState() => _CreateCaseSheetState();
}

class _CreateCaseSheetState extends State<_CreateCaseSheet> {
  final _title = TextEditingController();
  final _caseNumber = TextEditingController();
  final _court = TextEditingController();
  final _caseType = TextEditingController();
  final _opposite = TextEditingController();
  final _description = TextEditingController();
  final _cnr = TextEditingController();

  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _title.dispose();
    _caseNumber.dispose();
    _court.dispose();
    _caseType.dispose();
    _opposite.dispose();
    _description.dispose();
    _cnr.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_title.text.trim().length < 3) {
      setState(() {
        _error = 'Enter a case title of at least 3 characters.';
      });
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await context.read<ApiService>().createCitizenCase({
        'case_title': _title.text.trim(),
        'case_number': _caseNumber.text.trim().isEmpty
            ? null
            : _caseNumber.text.trim(),
        'case_type': _caseType.text.trim().isEmpty
            ? null
            : _caseType.text.trim(),
        'court_name': _court.text.trim().isEmpty ? null : _court.text.trim(),
        'opposite_party': _opposite.text.trim().isEmpty
            ? null
            : _opposite.text.trim(),
        'case_description': _description.text.trim().isEmpty
            ? null
            : _description.text.trim(),
        'cnr_number': _cnr.text.trim().isEmpty
            ? null
            : _cnr.text.trim().toUpperCase(),
        'court_source': 'eCourts India',
      });
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } on Exception catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e'.replaceFirst('ApiException: ', '');
      });
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(22)),
      ),
      child: SafeArea(
        top: false,
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(18, 12, 18, 18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Center(
                child: Container(
                  width: 42,
                  height: 4,
                  decoration: BoxDecoration(
                    color: AppColors.border,
                    borderRadius: BorderRadius.circular(999),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              const Text(
                'Register a legal matter',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 4),
              const Text(
                'Only the title is required. You can add court details later.',
                style: TextStyle(fontSize: 12, color: AppColors.muted),
              ),
              const SizedBox(height: 14),
              if (_error != null)
                Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppColors.danger.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(9),
                  ),
                  child: Text(
                    _error!,
                    style: const TextStyle(
                      color: AppColors.danger,
                      fontSize: 12,
                    ),
                  ),
                ),
              TextField(
                controller: _title,
                textCapitalization: TextCapitalization.sentences,
                decoration: const InputDecoration(labelText: 'Case title *'),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _caseType,
                decoration: const InputDecoration(
                  labelText: 'Case type',
                  hintText: 'Criminal, Civil, Consumer, Family…',
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _court,
                decoration: const InputDecoration(labelText: 'Court'),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _caseNumber,
                decoration: const InputDecoration(labelText: 'Case number'),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _opposite,
                decoration: const InputDecoration(labelText: 'Opposite party'),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _cnr,
                textCapitalization: TextCapitalization.characters,
                decoration: const InputDecoration(
                  labelText: 'eCourts CNR number',
                  hintText: '16-character CNR',
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _description,
                minLines: 3,
                maxLines: 6,
                textCapitalization: TextCapitalization.sentences,
                decoration: const InputDecoration(labelText: 'Description'),
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: _busy ? null : _save,
                child: _busy
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2.2,
                          color: Colors.white,
                        ),
                      )
                    : const Text('Register case'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CourtReferenceSheet extends StatefulWidget {
  const _CourtReferenceSheet({required this.caseId, required this.initial});

  final int caseId;
  final Future<Map<String, dynamic>> initial;

  @override
  State<_CourtReferenceSheet> createState() => _CourtReferenceSheetState();
}

class _CourtReferenceSheetState extends State<_CourtReferenceSheet> {
  final _cnr = TextEditingController();
  final _status = TextEditingController();
  final _url = TextEditingController();
  final _nextHearing = TextEditingController();
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    widget.initial
        .then((data) {
          if (!mounted) return;
          setState(() {
            _cnr.text = asString(data['cnr_number']);
            _status.text = asString(data['external_status']);
            _url.text = asString(data['official_case_url']);
            _nextHearing.text = asString(data['external_next_hearing_date']);
          });
        })
        .catchError((_) {});
  }

  @override
  void dispose() {
    _cnr.dispose();
    _status.dispose();
    _url.dispose();
    _nextHearing.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await context.read<ApiService>().updateCitizenCourtReference(
        widget.caseId,
        {
          'cnr_number': _cnr.text.trim().isEmpty
              ? null
              : _cnr.text.trim().toUpperCase(),
          'court_source': 'eCourts India',
          'official_case_url': _url.text.trim().isEmpty
              ? null
              : _url.text.trim(),
          'external_status': _status.text.trim().isEmpty
              ? null
              : _status.text.trim(),
          'external_next_hearing_date': _nextHearing.text.trim().isEmpty
              ? null
              : _nextHearing.text.trim(),
          'sync_hearing_reminder': true,
        },
      );
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } on Exception catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e'.replaceFirst('ApiException: ', '');
      });
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(22)),
      ),
      child: SafeArea(
        top: false,
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(18, 16, 18, 18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Update eCourts reference',
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 4),
              const Text(
                'VIDHIK stores the court reference you verify. It does not scrape or alter official court records.',
                style: TextStyle(
                  fontSize: 11.5,
                  color: AppColors.muted,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 14),
              if (_error != null)
                Text(
                  _error!,
                  style: const TextStyle(color: AppColors.danger, fontSize: 12),
                ),
              TextField(
                controller: _cnr,
                textCapitalization: TextCapitalization.characters,
                decoration: const InputDecoration(labelText: 'CNR number'),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _status,
                decoration: const InputDecoration(
                  labelText: 'Court status / stage',
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _nextHearing,
                decoration: const InputDecoration(
                  labelText: 'Next hearing date',
                  hintText: 'YYYY-MM-DD',
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _url,
                keyboardType: TextInputType.url,
                decoration: const InputDecoration(
                  labelText: 'Official case URL (optional)',
                ),
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: _busy ? null : _save,
                child: _busy
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2.2,
                          color: Colors.white,
                        ),
                      )
                    : const Text('Save court reference'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
