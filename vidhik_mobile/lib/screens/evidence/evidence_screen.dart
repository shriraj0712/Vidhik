import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/download_helper.dart';
import '../../core/utils/format.dart';
import '../../services/api_service.dart';
import '../../widgets/common.dart';

class EvidenceScreen extends StatefulWidget {
  const EvidenceScreen({super.key, this.selectMode = false});

  /// When true, an evidence item can be returned to the assistant for
  /// evidence-aware legal questions.
  final bool selectMode;

  @override
  State<EvidenceScreen> createState() => _EvidenceScreenState();
}

class _EvidenceScreenState extends State<EvidenceScreen> {
  late Future<Map<String, dynamic>> _future;
  bool _uploading = false;
  String? _uploadError;
  String? _processingStatus;

  @override
  void initState() {
    super.initState();
    _future = context.read<ApiService>().evidenceList();
  }

  Future<void> _reload() async {
    setState(() {
      _future = context.read<ApiService>().evidenceList();
    });
    await _future;
  }

  Future<void> _pickAndUpload() async {
    try {
      final file = await FilePicker.pickFile(
        type: FileType.custom,
        allowedExtensions: ['mp4', 'webm', 'mov', 'avi', 'mkv'],
      );
      if (file == null) return;
      if (file.path == null) {
        setState(() {
          _uploadError = 'The selected video could not be read.';
        });
        return;
      }
      setState(() {
        _uploading = true;
        _uploadError = null;
        _processingStatus = 'Uploading and hashing the recording…';
      });
      final response = await context.read<ApiService>().uploadEvidence(
        file.path!,
      );
      final evidenceId = asInt(response['evidence_id']);
      if (!mounted) return;
      setState(() {
        _uploading = false;
        _processingStatus = firstNonEmpty([
          response['processing_status'],
          'Processing audio and frames…',
        ]);
      });
      await _reload();
      if (!mounted) return;
      showInfoSnack(context, 'Evidence #$evidenceId uploaded securely.');
      await _pollStatus(evidenceId);
    } on Exception catch (e) {
      if (!mounted) return;
      setState(() {
        _uploading = false;
        _uploadError = '$e'.replaceFirst('ApiException: ', '');
      });
    }
  }

  Future<void> _pollStatus(int evidenceId) async {
    final api = context.read<ApiService>();
    for (var attempt = 0; attempt < 30; attempt++) {
      await Future<void>.delayed(const Duration(seconds: 5));
      if (!mounted) return;
      try {
        final detail = await api.evidenceDetail(evidenceId);
        final status = firstNonEmpty([detail['processing_status'], 'unknown']);
        if (!mounted) return;
        setState(() {
          _processingStatus = 'Processing status: $status';
        });
        if (status == 'completed' ||
            status == 'failed' ||
            status == 'error' ||
            status == 'completed_with_warnings') {
          await _reload();
          if (!mounted) return;
          setState(() {
            _processingStatus = null;
          });
          _openDetail(evidenceId);
          return;
        }
      } catch (e) {
        if (!mounted) return;
        setState(() {
          _processingStatus = 'Status check failed: $e';
        });
        return;
      }
    }
    if (mounted) {
      setState(
        () => _processingStatus = 'Processing is taking longer than expected. Pull to refresh for updates.',
      );
    }
  }

  Future<void> _openDetail(int evidenceId) async {
    final api = context.read<ApiService>();
    try {
      final detail = await api.evidenceDetail(evidenceId);
      if (!mounted) return;
      final selected = await Navigator.of(context).push<int>(
        MaterialPageRoute(
          builder: (_) => EvidenceDetailScreen(
            evidence: detail,
            selectMode: widget.selectMode,
          ),
        ),
      );
      if (!mounted) return;
      if (widget.selectMode && selected != null) {
        Navigator.of(context).pop(selected);
        return;
      }
      _reload();
    } on Exception catch (e) {
      if (mounted) showErrorSnack(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.selectMode ? 'Attach video evidence' : 'Video evidence',
        ),
        actions: [
          IconButton(onPressed: _reload, icon: const Icon(Icons.refresh)),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _uploading ? null : _pickAndUpload,
        backgroundColor: AppColors.teal,
        foregroundColor: Colors.white,
        icon: _uploading
            ? const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Colors.white,
                ),
              )
            : const Icon(Icons.video_call_outlined),
        label: Text(_uploading ? 'Uploading…' : 'Upload video'),
      ),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 90),
          children: [
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.security, size: 18, color: AppColors.teal),
                      SizedBox(width: 7),
                      Text(
                        'Chain of custody',
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Recordings are hashed with SHA-256 on upload and stored by the backend. Frame observations and '
                    'transcripts are machine-generated and explicitly marked as such. Under BSA, 2023 section 63, '
                    'electronic evidence requires preservation of the original and a certificate for court use.',
                    style: TextStyle(
                      fontSize: 11.5,
                      color: AppColors.muted,
                      height: 1.45,
                    ),
                  ),
                ],
              ),
            ),
            if (_uploadError != null) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppColors.danger.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(9),
                ),
                child: Text(
                  _uploadError!,
                  style: const TextStyle(color: AppColors.danger, fontSize: 12),
                ),
              ),
            ],
            if (_processingStatus != null) ...[
              const SizedBox(height: 10),
              AppCard(
                child: Row(
                  children: [
                    const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        _processingStatus!,
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.muted,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 12),
            FutureBuilder<Map<String, dynamic>>(
              future: _future,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(
                    child: Padding(
                      padding: EdgeInsets.all(24),
                      child: CircularProgressIndicator(strokeWidth: 2.4),
                    ),
                  );
                }
                if (snapshot.hasError) {
                  return ErrorState(
                    message: '${snapshot.error}'.replaceFirst(
                      'ApiException: ',
                      '',
                    ),
                    onRetry: _reload,
                  );
                }
                final items = asMapList(asMap(snapshot.data)['items']);
                if (items.isEmpty) {
                  return const EmptyState(
                    title: 'No evidence uploaded',
                    message: 'Upload an MP4, WebM, MOV, AVI or MKV recording to extract transcripts and observable events.',
                    icon: Icons.video_library_outlined,
                  );
                }
                return Column(
                  children: [
                    for (final item in items)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 9),
                        child: AppCard(
                          onTap: () => _openDetail(asInt(item['evidence_id'])),
                          child: Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.all(9),
                                decoration: BoxDecoration(
                                  color: AppColors.navy.withValues(alpha: 0.06),
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: const Icon(
                                  Icons.videocam,
                                  size: 19,
                                  color: AppColors.navy,
                                ),
                              ),
                              const SizedBox(width: 11),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      firstNonEmpty([
                                        item['original_filename'],
                                        'Recording',
                                      ]),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(
                                        fontWeight: FontWeight.w600,
                                        fontSize: 13,
                                      ),
                                    ),
                                    const SizedBox(height: 3),
                                    Text(
                                      'EVD-${item['evidence_id']} · ${firstNonEmpty([item['media_container'], ''])}'
                                      '${item['duration_seconds'] != null ? ' · ${asDouble(item['duration_seconds']).toStringAsFixed(1)}s' : ''}',
                                      style: const TextStyle(
                                        fontSize: 11,
                                        color: AppColors.muted,
                                      ),
                                    ),
                                    const SizedBox(height: 5),
                                    Tag(
                                      firstNonEmpty([
                                        item['processing_status'],
                                        'uploaded',
                                      ]).replaceAll('_', ' ').toUpperCase(),
                                      color:
                                          asString(item['processing_status']) ==
                                              'failed'
                                          ? AppColors.danger
                                          : AppColors.teal,
                                    ),
                                  ],
                                ),
                              ),
                              const Icon(
                                Icons.chevron_right,
                                color: AppColors.muted,
                              ),
                            ],
                          ),
                        ),
                      ),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

class EvidenceDetailScreen extends StatelessWidget {
  const EvidenceDetailScreen({
    super.key,
    required this.evidence,
    this.selectMode = false,
  });

  final Map<String, dynamic> evidence;
  final bool selectMode;

  Future<void> _download(BuildContext context) async {
    try {
      final result = await context.read<ApiService>().downloadEvidenceReport(
        asInt(evidence['evidence_id']),
      );
      await shareDownloadedBytes(
        bytes: result.bytes,
        filename: result.filename,
        subject: 'VIDHIK evidence report',
      );
    } on Exception catch (e) {
      if (context.mounted) showErrorSnack(context, e);
    }
  }

  Future<void> _retry(BuildContext context) async {
    try {
      await context.read<ApiService>().retryEvidence(
        asInt(evidence['evidence_id']),
      );
      if (context.mounted) showInfoSnack(context, 'Reprocessing queued.');
    } on Exception catch (e) {
      if (context.mounted) showErrorSnack(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final transcripts = asMapList(evidence['transcripts']);
    final observations = asMapList(evidence['observations']);
    final report = asMap(evidence['report']);
    final status = firstNonEmpty([evidence['processing_status'], 'unknown']);
    final failed = status == 'failed' || status == 'error';

    return Scaffold(
      appBar: AppBar(
        title: Text('EVD-${evidence['evidence_id']}'),
        actions: [
          IconButton(
            tooltip: 'Download report',
            onPressed: () => _download(context),
            icon: const Icon(Icons.download_outlined),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 30),
        children: [
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  firstNonEmpty([evidence['original_filename'], 'Recording']),
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 6,
                  runSpacing: 5,
                  children: [
                    Tag(
                      status.replaceAll('_', ' ').toUpperCase(),
                      color: failed ? AppColors.danger : AppColors.teal,
                    ),
                    Tag(firstNonEmpty([evidence['media_container'], 'video'])),
                    if (evidence['has_audio'] == false)
                      const Tag('No audio', color: AppColors.warning),
                  ],
                ),
                const SizedBox(height: 10),
                InfoRow(
                  'Resolution',
                  firstNonEmpty([evidence['resolution'], '—']),
                ),
                InfoRow(
                  'Duration',
                  evidence['duration_seconds'] == null
                      ? '—'
                      : '${asDouble(evidence['duration_seconds']).toStringAsFixed(1)} seconds',
                ),
                InfoRow(
                  'SHA-256',
                  firstNonEmpty([evidence['file_hash_sha256'], '—']),
                ),
                if (asString(evidence['error_message']).isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text(
                      asString(evidence['error_message']),
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppColors.danger,
                      ),
                    ),
                  ),
                if (failed) ...[
                  const SizedBox(height: 10),
                  OutlinedButton.icon(
                    onPressed: () => _retry(context),
                    icon: const Icon(Icons.refresh, size: 18),
                    label: const Text('Retry processing'),
                  ),
                ],
              ],
            ),
          ),
          if (selectMode) ...[
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: () =>
                  Navigator.of(context).pop(asInt(evidence['evidence_id'])),
              icon: const Icon(Icons.attach_file),
              label: const Text('Attach to my next question'),
            ),
          ],
          if (report.isNotEmpty) ...[
            const SizedBox(height: 14),
            const SectionTitle('AI-structured report'),
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    asString(report['summary']),
                    style: const TextStyle(fontSize: 12.5, height: 1.5),
                  ),
                  if (asMapList(report['technical_limitations'])
                      .isNotEmpty) ...[
                    const SizedBox(height: 10),
                    const Text(
                      'Technical limitations',
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 12.5,
                      ),
                    ),
                    const SizedBox(height: 5),
                    BulletList(
                      asMapList(report['technical_limitations'])
                          .map((e) => asString(e))
                          .where((e) => e.isNotEmpty)
                          .toList(),
                    ),
                  ],
                  if (asMapList(report['preservation_guidelines'])
                      .isNotEmpty) ...[
                    const SizedBox(height: 10),
                    const Text(
                      'Preservation guidance',
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 12.5,
                      ),
                    ),
                    const SizedBox(height: 5),
                    BulletList(
                      asMapList(report['preservation_guidelines'])
                          .map((e) => asString(e))
                          .where((e) => e.isNotEmpty)
                          .toList(),
                    ),
                  ],
                ],
              ),
            ),
          ],
          const SizedBox(height: 14),
          SectionTitle('Observable events (${observations.length})'),
          if (observations.isEmpty)
            const AppCard(
              child: Text(
                'No frame observations recorded.',
                style: TextStyle(color: AppColors.muted),
              ),
            )
          else
            for (final observation in observations)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        firstNonEmpty([
                          observation['time_formatted'],
                          if (observation['timestamp_seconds'] != null)
                            '${asDouble(observation['timestamp_seconds']).toStringAsFixed(0)}s',
                        ]),
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: AppColors.teal,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        firstNonEmpty([observation['observation'], '']),
                        style: const TextStyle(fontSize: 12.5, height: 1.4),
                      ),
                      if (asString(observation['limitations']).isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text(
                          'Limitation: ${observation['limitations']}',
                          style: const TextStyle(
                            fontSize: 10.5,
                            color: AppColors.muted,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
          const SizedBox(height: 14),
          SectionTitle('Transcript (${transcripts.length})'),
          if (transcripts.isEmpty)
            const AppCard(
              child: Text(
                'No transcript available.',
                style: TextStyle(color: AppColors.muted),
              ),
            )
          else
            for (final segment in transcripts)
              Padding(
                padding: const EdgeInsets.only(bottom: 7),
                child: AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        firstNonEmpty([
                          segment['time_formatted'],
                          if (segment['start_time'] != null)
                            '${asDouble(segment['start_time']).toStringAsFixed(1)}s',
                        ]),
                        style: const TextStyle(
                          fontSize: 10.5,
                          fontWeight: FontWeight.w700,
                          color: AppColors.teal,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        firstNonEmpty([segment['text'], '']),
                        style: const TextStyle(fontSize: 12.5, height: 1.4),
                      ),
                      if (asString(segment['speaker']).isNotEmpty)
                        Text(
                          asString(segment['speaker']),
                          style: const TextStyle(
                            fontSize: 10.5,
                            color: AppColors.muted,
                          ),
                        ),
                    ],
                  ),
                ),
              ),
          const SizedBox(height: 12),
          Text(
            'Machine-generated observations are not findings of fact. Review the original recording before relying on them.',
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 10.5,
              color: AppColors.muted,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }
}
