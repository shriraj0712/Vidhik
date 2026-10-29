import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/format.dart';
import '../../models/citizen.dart';
import '../../services/api_service.dart';
import '../../widgets/common.dart';

/// eCourts tracking is reference-based: VIDHIK stores the CNR and court details
/// a citizen verifies, and links out to the official eCourts service. The app
/// does not scrape or mutate official court records.
class CaseTrackingScreen extends StatefulWidget {
  const CaseTrackingScreen({super.key, this.caseId});

  final int? caseId;

  @override
  State<CaseTrackingScreen> createState() => _CaseTrackingScreenState();
}

class _CaseTrackingScreenState extends State<CaseTrackingScreen> {
  late Future<List<CitizenCase>> _casesFuture;
  int? _selectedCaseId;

  @override
  void initState() {
    super.initState();
    _selectedCaseId = widget.caseId;
    _casesFuture = context.read<ApiService>().citizenCases();
  }

  void _reloadCases() {
    setState(() {
      _casesFuture = context.read<ApiService>().citizenCases();
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_selectedCaseId != null) {
      return _TrackingDetail(
        caseId: _selectedCaseId!,
        onBack: widget.caseId == null
            ? () => setState(() => _selectedCaseId = null)
            : null,
      );
    }
    return Scaffold(
      appBar: AppBar(title: const Text('eCourts case tracking')),
      body: FutureBuilder<List<CitizenCase>>(
        future: _casesFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(
              child: CircularProgressIndicator(strokeWidth: 2.4),
            );
          }
          if (snapshot.hasError) {
            return ErrorState(
              message: '${snapshot.error}'.replaceFirst('ApiException: ', ''),
              onRetry: _reloadCases,
            );
          }
          final cases = snapshot.data ?? const [];
          if (cases.isEmpty) {
            return const EmptyState(
              title: 'No cases to track',
              message:
                  'Register a matter first, then add its eCourts CNR number.',
              icon: Icons.track_changes,
            );
          }
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
            children: [
              const AppCard(
                child: Text(
                  'Choose a matter to view its stored court reference. To refresh the official status, search the '
                  'CNR on the eCourts website and update the reference here.',
                  style: TextStyle(
                    fontSize: 12,
                    color: AppColors.muted,
                    height: 1.45,
                  ),
                ),
              ),
              const SizedBox(height: 12),
              for (final item in cases)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: AppCard(
                    onTap: () => setState(() => _selectedCaseId = item.caseId),
                    child: Row(
                      children: [
                        const Icon(
                          Icons.gavel,
                          color: AppColors.teal,
                          size: 19,
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                item.title,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w600,
                                  fontSize: 13.5,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                item.cnrNumber == null
                                    ? 'No CNR linked'
                                    : 'CNR ${item.cnrNumber}',
                                style: TextStyle(
                                  fontSize: 11,
                                  color: item.cnrNumber == null
                                      ? AppColors.warning
                                      : AppColors.muted,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const Icon(Icons.chevron_right, color: AppColors.muted),
                      ],
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}

class _TrackingDetail extends StatefulWidget {
  const _TrackingDetail({required this.caseId, this.onBack});

  final int caseId;
  final VoidCallback? onBack;

  @override
  State<_TrackingDetail> createState() => _TrackingDetailState();
}

class _TrackingDetailState extends State<_TrackingDetail> {
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

  Future<void> _edit() async {
    final data = await _future;
    if (!mounted) return;
    final changed = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) =>
          _CourtReferenceEditor(caseId: widget.caseId, initial: data),
    );
    if (changed == true) _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: widget.onBack == null
            ? null
            : IconButton(
                onPressed: widget.onBack,
                icon: const Icon(Icons.arrow_back),
              ),
        title: const Text('Court reference'),
        actions: [
          IconButton(onPressed: _reload, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: AsyncView<Map<String, dynamic>>(
        future: _future,
        onRetry: _reload,
        loadingText: 'Loading court reference…',
        builder: (context, data) {
          final item = CitizenCase.fromJson(data);
          final cnr = item.cnrNumber ?? '';
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 30),
            children: [
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item.title,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 8),
                    InfoRow('CNR number', cnr.isEmpty ? 'Not linked' : cnr),
                    InfoRow('Court', item.courtName ?? '—'),
                    InfoRow('Case number', item.caseNumber ?? '—'),
                    InfoRow('Court status', item.externalStatus ?? '—'),
                    InfoRow('Next hearing', formatDate(item.nextHearingDate)),
                    InfoRow(
                      'Source',
                      asString(data['court_source'], 'eCourts India'),
                    ),
                    InfoRow(
                      'Last verified',
                      formatDateTime(data['last_verified_at']),
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        if (cnr.isNotEmpty)
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: () {
                                Clipboard.setData(ClipboardData(text: cnr));
                                showInfoSnack(
                                  context,
                                  'CNR copied. Paste it on eCourts.',
                                );
                              },
                              icon: const Icon(Icons.copy, size: 17),
                              label: const Text('Copy CNR'),
                            ),
                          ),
                        if (cnr.isNotEmpty) const SizedBox(width: 8),
                        Expanded(
                          child: FilledButton.icon(
                            onPressed: _edit,
                            icon: const Icon(Icons.edit_outlined, size: 17),
                            label: const Text('Update'),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              ExternalLinkButton(
                url: 'https://services.ecourts.gov.in/ecourtindia_v6/',
                label: 'Search on official eCourts',
              ),
              const SizedBox(height: 14),
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'How verification works',
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 13,
                      ),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      '1. Copy the CNR above.\n'
                      '2. Open eCourts and search by CNR.\n'
                      '3. Return here and save the current stage and next hearing date.\n\n'
                      'VIDHIK does not fetch, modify or replace official court records. The stored values are the '
                      'ones you verify and enter.',
                      style: TextStyle(
                        fontSize: 12,
                        height: 1.5,
                        color: AppColors.muted,
                      ),
                    ),
                  ],
                ),
              ),
              if (asString(item.officialCaseUrl).isNotEmpty) ...[
                const SizedBox(height: 10),
                ExternalLinkButton(
                  url: item.officialCaseUrl!,
                  label: 'Open saved case URL',
                ),
              ],
            ],
          );
        },
      ),
    );
  }
}

class _CourtReferenceEditor extends StatefulWidget {
  const _CourtReferenceEditor({required this.caseId, required this.initial});

  final int caseId;
  final Map<String, dynamic> initial;

  @override
  State<_CourtReferenceEditor> createState() => _CourtReferenceEditorState();
}

class _CourtReferenceEditorState extends State<_CourtReferenceEditor> {
  late final TextEditingController _cnr;
  late final TextEditingController _status;
  late final TextEditingController _nextHearing;
  late final TextEditingController _url;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _cnr = TextEditingController(text: asString(widget.initial['cnr_number']));
    _status = TextEditingController(
      text: asString(widget.initial['external_status']),
    );
    _nextHearing = TextEditingController(
      text: asString(widget.initial['external_next_hearing_date']),
    );
    _url = TextEditingController(
      text: asString(widget.initial['official_case_url']),
    );
  }

  @override
  void dispose() {
    _cnr.dispose();
    _status.dispose();
    _nextHearing.dispose();
    _url.dispose();
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
      if (mounted) {
        setState(() {
          _error = '$e'.replaceFirst('ApiException: ', '');
        });
      }
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
                'Update court reference',
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 4),
              const Text(
                'Enter what you verified on the official eCourts site.',
                style: TextStyle(fontSize: 11.5, color: AppColors.muted),
              ),
              const SizedBox(height: 12),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(
                    _error!,
                    style: const TextStyle(
                      color: AppColors.danger,
                      fontSize: 12,
                    ),
                  ),
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
              const SizedBox(height: 14),
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
                    : const Text('Save reference'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
