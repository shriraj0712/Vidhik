import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/download_helper.dart';
import '../../core/utils/format.dart';
import '../../providers/auth_provider.dart';
import '../../providers/settings_provider.dart';
import '../../services/api_service.dart';
import '../../widgets/common.dart';

// ---------------------------------------------------------------------------
// Resolution decision engine
// ---------------------------------------------------------------------------

class ResolutionScreen extends StatefulWidget {
  const ResolutionScreen({super.key});

  @override
  State<ResolutionScreen> createState() => _ResolutionScreenState();
}

class _ResolutionScreenState extends State<ResolutionScreen> {
  final _situation = TextEditingController();
  final _amount = TextEditingController();
  String? _category;
  bool _police = false;
  bool _courtNotice = false;
  bool _arrestThreat = false;
  bool _physicalDanger = false;
  bool _children = false;
  bool _domestic = false;
  bool _deadline = false;

  bool _busy = false;
  String? _error;
  Map<String, dynamic>? _result;

  static const _categories = [
    'Criminal',
    'Family',
    'Consumer',
    'Property',
    'RTI',
    'Traffic',
    'Employment',
    'Cyber',
    'Other',
  ];

  @override
  void dispose() {
    _situation.dispose();
    _amount.dispose();
    super.dispose();
  }

  Future<void> _evaluate() async {
    if (_situation.text.trim().length < 10) {
      setState(() {
        _error = 'Describe your situation in at least 10 characters.';
      });
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
      _result = null;
    });
    try {
      final language = context.read<SettingsProvider>().language;
      final result = await context.read<ApiService>().evaluateResolution({
        'situation': _situation.text.trim(),
        'issue_category': _category,
        'jurisdiction': 'India',
        'monetary_amount': double.tryParse(
          _amount.text.trim().replaceAll(',', ''),
        ),
        'has_police_involvement': _police,
        'has_court_notice': _courtNotice,
        'has_arrest_threat': _arrestThreat,
        'is_physical_danger': _physicalDanger,
        'involves_children': _children,
        'involves_domestic_violence': _domestic,
        'has_urgent_deadline': _deadline,
        'language': language,
      });
      if (!mounted) return;
      setState(() {
        _result = result;
      });
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
    return Scaffold(
      appBar: AppBar(title: const Text('Resolution advisor')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 30),
        children: [
          const AppCard(
            child: Text(
              'Describe the dispute. Vidhik determines whether it is realistically self-resolvable, needs an advocate, '
              'or requires urgent legal intervention, based on deterministic statutory rules.',
              style: TextStyle(
                fontSize: 12.5,
                height: 1.5,
                color: AppColors.muted,
              ),
            ),
          ),
          const SizedBox(height: 12),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Text(
                _error!,
                style: const TextStyle(
                  color: AppColors.danger,
                  fontSize: 12,
                  height: 1.4,
                ),
              ),
            ),
          TextField(
            controller: _situation,
            minLines: 4,
            maxLines: 8,
            textCapitalization: TextCapitalization.sentences,
            decoration: const InputDecoration(
              labelText: 'Your situation *',
              alignLabelWithHint: true,
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: DropdownButtonFormField<String>(
                  initialValue: _category,
                  isExpanded: true,
                  decoration: const InputDecoration(labelText: 'Category'),
                  items: [
                    const DropdownMenuItem(
                      value: null,
                      child: Text('Not sure'),
                    ),
                    for (final category in _categories)
                      DropdownMenuItem(value: category, child: Text(category)),
                  ],
                  onChanged: (value) => setState(() => _category = value),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: TextField(
                  controller: _amount,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Amount (₹)'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          const Text(
            'Relevant circumstances',
            style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
          ),
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: [
              _flag(
                'Police involved',
                _police,
                (v) => setState(() => _police = v),
              ),
              _flag(
                'Court notice',
                _courtNotice,
                (v) => setState(() => _courtNotice = v),
              ),
              _flag(
                'Arrest threat',
                _arrestThreat,
                (v) => setState(() => _arrestThreat = v),
              ),
              _flag(
                'Physical danger',
                _physicalDanger,
                (v) => setState(() => _physicalDanger = v),
              ),
              _flag(
                'Children involved',
                _children,
                (v) => setState(() => _children = v),
              ),
              _flag(
                'Domestic violence',
                _domestic,
                (v) => setState(() => _domestic = v),
              ),
              _flag(
                'Urgent deadline',
                _deadline,
                (v) => setState(() => _deadline = v),
              ),
            ],
          ),
          const SizedBox(height: 14),
          FilledButton.icon(
            onPressed: _busy ? null : _evaluate,
            icon: _busy
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Icon(Icons.balance),
            label: Text(_busy ? 'Evaluating…' : 'Evaluate my options'),
          ),
          if (_result != null) ...[
            const SizedBox(height: 20),
            _resolutionResult(_result!),
          ],
        ],
      ),
    );
  }

  Widget _flag(String label, bool value, ValueChanged<bool> onChanged) {
    return FilterChip(
      label: Text(label, style: const TextStyle(fontSize: 11.5)),
      selected: value,
      onSelected: onChanged,
    );
  }

  Widget _resolutionResult(Map<String, dynamic> result) {
    final type = firstNonEmpty([result['recommendation_type'], 'unknown']);
    final risk = firstNonEmpty([result['risk_level'], 'medium']);
    final guidance = asMap(result['emergency_guidance']);
    final procedures = asMapList(result['relevant_procedures']);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.riskColor(risk).withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: AppColors.riskColor(risk).withValues(alpha: 0.3),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      _recommendationLabel(type),
                      style: TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 15,
                        color: AppColors.riskColor(risk),
                      ),
                    ),
                  ),
                  Tag(
                    '${risk.toUpperCase()} RISK',
                    color: AppColors.riskColor(risk),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                asString(result['primary_reason']),
                style: const TextStyle(fontSize: 13, height: 1.5),
              ),
            ],
          ),
        ),
        if (asMapList(result['reasons']).isNotEmpty) ...[
          const SizedBox(height: 14),
          const SectionTitle('Why'),
          AppCard(
            child: BulletList(
              asMapList(result['reasons'])
                  .map((e) => asString(e))
                  .where((e) => e.isNotEmpty)
                  .toList(),
            ),
          ),
        ],
        if (asMapList(result['next_steps']).isNotEmpty) ...[
          const SizedBox(height: 14),
          const SectionTitle('Immediate next steps'),
          AppCard(
            child: BulletList(
              asMapList(result['next_steps'])
                  .map((e) => asString(e))
                  .where((e) => e.isNotEmpty)
                  .toList(),
              numbered: true,
            ),
          ),
        ],
        if (asMapList(result['self_help_checklist']).isNotEmpty) ...[
          const SizedBox(height: 14),
          const SectionTitle('Self-help checklist'),
          AppCard(
            child: BulletList(
              asMapList(result['self_help_checklist'])
                  .map((e) => asString(e))
                  .where((e) => e.isNotEmpty)
                  .toList(),
              numbered: true,
            ),
          ),
        ],
        if (asString(result['lawyer_specialization_needed']).isNotEmpty) ...[
          const SizedBox(height: 14),
          AppCard(
            child: InfoRow(
              'Advocate needed',
              asString(result['lawyer_specialization_needed']),
            ),
          ),
        ],
        if (asMapList(result['applicable_areas']).isNotEmpty) ...[
          const SizedBox(height: 10),
          AppCard(
            child: Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final area in asMapList(result['applicable_areas']))
                  Tag(asString(area)),
              ],
            ),
          ),
        ],
        if (guidance.isNotEmpty) ...[
          const SizedBox(height: 14),
          const SectionTitle('Emergency guidance'),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (asString(guidance['message']).isNotEmpty)
                  Text(
                    asString(guidance['message']),
                    style: const TextStyle(fontSize: 12.5, height: 1.45),
                  ),
                const SizedBox(height: 6),
                if (asString(guidance['national_emergency']).isNotEmpty)
                  InfoRow(
                    'National emergency',
                    asString(guidance['national_emergency']),
                  ),
                if (guidance['helplines'] is List)
                  BulletList(
                    (guidance['helplines'] as List)
                        .map((e) => asString(e))
                        .where((e) => e.isNotEmpty)
                        .toList(),
                  ),
              ],
            ),
          ),
        ],
        if (procedures.isNotEmpty) ...[
          const SizedBox(height: 14),
          const SectionTitle('Related procedures'),
          for (final procedure in procedures)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: AppCard(
                child: Text(
                  firstNonEmpty([
                    procedure['procedure_name'],
                    procedure['title'],
                    'Procedure',
                  ]),
                  style: const TextStyle(
                    fontSize: 12.5,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ),
        ],
        const SizedBox(height: 12),
        Text(
          asString(result['disclaimer']),
          style: const TextStyle(
            fontSize: 10.5,
            color: AppColors.muted,
            height: 1.4,
          ),
        ),
      ],
    );
  }

  String _recommendationLabel(String type) {
    switch (type) {
      case 'self_resolvable':
        return 'You may be able to resolve this yourself';
      case 'lawyer_consultation_required':
        return 'Consult a qualified advocate';
      case 'urgent_legal_intervention':
        return 'Urgent legal intervention recommended';
      default:
        return 'Legal triage result';
    }
  }
}

// ---------------------------------------------------------------------------
// Traffic law engine
// ---------------------------------------------------------------------------

class TrafficLawScreen extends StatefulWidget {
  const TrafficLawScreen({super.key});

  @override
  State<TrafficLawScreen> createState() => _TrafficLawScreenState();
}

class _TrafficLawScreenState extends State<TrafficLawScreen> {
  final _description = TextEditingController();
  final _challan = TextEditingController();
  final _state = TextEditingController(text: 'General / Pan-India');
  String _vehicle = 'two_wheeler';
  bool _busy = false;
  String? _error;
  Map<String, dynamic>? _result;

  @override
  void initState() {
    super.initState();
    _loadOffences();
  }

  List<Map<String, dynamic>> _offences = [];

  Future<void> _loadOffences() async {
    try {
      final offences = await context.read<ApiService>().trafficOffences();
      if (mounted) {
        setState(() {
          _offences = offences;
        });
      }
    } catch (_) {
      // Reference list is optional.
    }
  }

  @override
  void dispose() {
    _description.dispose();
    _challan.dispose();
    _state.dispose();
    super.dispose();
  }

  Future<void> _analyse() async {
    if (_description.text.trim().length < 3) {
      setState(() {
        _error = 'Describe the traffic issue or challan.';
      });
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
      _result = null;
    });
    try {
      final result = await context.read<ApiService>().analyzeTraffic({
        'violation_description': _description.text.trim(),
        'challan_number': _challan.text.trim().isEmpty
            ? null
            : _challan.text.trim(),
        'vehicle_type': _vehicle,
        'state': _state.text.trim(),
      });
      if (mounted) {
        setState(() {
          _result = result;
        });
      }
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
    final primary = asMap(_result?['primary_offence']);
    final related = asMapList(_result?['related_offences']);
    return Scaffold(
      appBar: AppBar(title: const Text('Traffic law & fines')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 30),
        children: [
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Motor Vehicles Act analysis',
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                ),
                const SizedBox(height: 5),
                const Text(
                  'Identifies applicable MVA sections, statutory penalties, licence consequences and the process to dispute an incorrect e-challan.',
                  style: TextStyle(
                    fontSize: 12,
                    color: AppColors.muted,
                    height: 1.45,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Text(
                _error!,
                style: const TextStyle(color: AppColors.danger, fontSize: 12),
              ),
            ),
          TextField(
            controller: _description,
            minLines: 3,
            maxLines: 6,
            decoration: const InputDecoration(
              labelText: 'What happened? *',
              hintText: 'For example: I was stopped for riding without a helmet in Pune…',
              alignLabelWithHint: true,
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _challan,
            decoration: const InputDecoration(
              labelText: 'e-Challan number (optional)',
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: DropdownButtonFormField<String>(
                  initialValue: _vehicle,
                  decoration: const InputDecoration(labelText: 'Vehicle type'),
                  items: const [
                    DropdownMenuItem(
                      value: 'two_wheeler',
                      child: Text('Two-wheeler'),
                    ),
                    DropdownMenuItem(
                      value: 'four_wheeler',
                      child: Text('Four-wheeler'),
                    ),
                    DropdownMenuItem(
                      value: 'commercial',
                      child: Text('Commercial'),
                    ),
                  ],
                  onChanged: (value) =>
                      setState(() => _vehicle = value ?? 'two_wheeler'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: TextField(
                  controller: _state,
                  decoration: const InputDecoration(labelText: 'State'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          FilledButton.icon(
            onPressed: _busy ? null : _analyse,
            icon: _busy
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Icon(Icons.traffic_outlined),
            label: Text(_busy ? 'Analysing…' : 'Analyse violation'),
          ),
          if (_result != null) ...[
            const SizedBox(height: 18),
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    firstNonEmpty([
                      primary['offence_name'],
                      'Identified offence',
                    ]),
                    style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 8),
                  InfoRow(
                    'MVA section',
                    firstNonEmpty([primary['mva_section'], '—']),
                  ),
                  InfoRow(
                    'Penalty',
                    firstNonEmpty([primary['statutory_penalty_range'], '—']),
                  ),
                  InfoRow(
                    'Licence',
                    firstNonEmpty([primary['license_consequence'], '—']),
                  ),
                  InfoRow(
                    'Court required',
                    primary['court_appearance_required'] == true ? 'Yes' : 'No',
                  ),
                ],
              ),
            ),
            if (related.isNotEmpty) ...[
              const SizedBox(height: 12),
              const SectionTitle('Related offences'),
              for (final offence in related)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: AppCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          firstNonEmpty([offence['offence_name'], 'Offence']),
                          style: const TextStyle(
                            fontWeight: FontWeight.w600,
                            fontSize: 13,
                          ),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          firstNonEmpty([offence['mva_section'], '']),
                          style: const TextStyle(
                            fontSize: 11,
                            color: AppColors.teal,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          firstNonEmpty([
                            offence['statutory_penalty_range'],
                            '',
                          ]),
                          style: const TextStyle(fontSize: 12, height: 1.4),
                        ),
                      ],
                    ),
                  ),
                ),
            ],
            const SizedBox(height: 12),
            _listCard(
              'Documents to carry',
              asMapList(_result!['mandatory_documents']),
            ),
            _listCard(
              'How to dispute',
              asMapList(_result!['dispute_challenge_process']),
              numbered: true,
            ),
            _listCard(
              'Official portals',
              asMapList(_result!['online_payment_portals']),
            ),
            const SizedBox(height: 10),
            Text(
              asString(_result!['disclaimer']),
              style: const TextStyle(
                fontSize: 10.5,
                color: AppColors.muted,
                height: 1.4,
              ),
            ),
          ],
          if (_offences.isNotEmpty) ...[
            const SizedBox(height: 18),
            const SectionTitle('Common offences'),
            AppCard(
              child: Column(
                children: [
                  for (final offence in _offences.take(8))
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            firstNonEmpty([offence['name'], 'Offence']),
                            style: const TextStyle(
                              fontSize: 12.5,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          Text(
                            firstNonEmpty([offence['penalty'], '']),
                            style: const TextStyle(
                              fontSize: 11,
                              color: AppColors.muted,
                              height: 1.35,
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _listCard(
    String title,
    List<Map<String, dynamic>> items, {
    bool numbered = false,
  }) {
    final values = items
        .map((e) => asString(e))
        .where((e) => e.isNotEmpty)
        .toList();
    if (values.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
            ),
            const SizedBox(height: 8),
            BulletList(values, numbered: numbered),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Constitutional rights
// ---------------------------------------------------------------------------

class ConstitutionalRightsScreen extends StatefulWidget {
  const ConstitutionalRightsScreen({super.key});

  @override
  State<ConstitutionalRightsScreen> createState() =>
      _ConstitutionalRightsScreenState();
}

class _ConstitutionalRightsScreenState
    extends State<ConstitutionalRightsScreen> {
  final _facts = TextEditingController();
  bool _busy = false;
  String? _error;
  Map<String, dynamic>? _result;
  late Future<List<Map<String, dynamic>>> _rightsFuture;

  @override
  void initState() {
    super.initState();
    _rightsFuture = context.read<ApiService>().constitutionalRights();
  }

  @override
  void dispose() {
    _facts.dispose();
    super.dispose();
  }

  Future<void> _analyse() async {
    if (_facts.text.trim().length < 5) {
      setState(() {
        _error = 'Describe the facts in a few words.';
      });
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
      _result = null;
    });
    try {
      final language = context.read<SettingsProvider>().language;
      final result = await context.read<ApiService>().analyzeConstitutional({
        'facts': _facts.text.trim(),
        'language': language,
      });
      if (mounted) {
        setState(() {
          _result = result;
        });
      }
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
    final rights = asMapList(_result?['primary_rights_engaged']);
    return Scaffold(
      appBar: AppBar(title: const Text('Constitutional rights')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 30),
        children: [
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Fundamental Rights & writ remedies',
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                ),
                const SizedBox(height: 5),
                const Text(
                  'Describe a situation involving state action, police conduct, detention or a denial of a public service. '
                  'Vidhik identifies the Articles potentially engaged and the writ remedy route.',
                  style: TextStyle(
                    fontSize: 12,
                    color: AppColors.muted,
                    height: 1.45,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Text(
                _error!,
                style: const TextStyle(color: AppColors.danger, fontSize: 12),
              ),
            ),
          TextField(
            controller: _facts,
            minLines: 4,
            maxLines: 8,
            decoration: const InputDecoration(
              labelText: 'What happened? *',
              alignLabelWithHint: true,
            ),
          ),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: _busy ? null : _analyse,
            icon: _busy
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Icon(Icons.account_balance),
            label: Text(_busy ? 'Analysing…' : 'Analyse rights'),
          ),
          if (_result != null) ...[
            const SizedBox(height: 18),
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          asBool(_result!['is_state_action_involved'])
                              ? 'State action appears involved'
                              : 'No clear state action detected',
                          style: const TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 14,
                          ),
                        ),
                      ),
                      Tag(
                        asBool(_result!['is_state_action_involved'])
                            ? 'Article 32 / 226'
                            : 'Review',
                        color: asBool(_result!['is_state_action_involved'])
                            ? AppColors.teal
                            : AppColors.warning,
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    asString(_result!['summary_analysis']),
                    style: const TextStyle(fontSize: 13, height: 1.5),
                  ),
                ],
              ),
            ),
            if (rights.isNotEmpty) ...[
              const SizedBox(height: 14),
              const SectionTitle('Rights engaged'),
              for (final right in rights)
                Padding(
                  padding: const EdgeInsets.only(bottom: 9),
                  child: AppCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                '${firstNonEmpty([right['article'], 'Article'])} — ${firstNonEmpty([right['title'], ''])}',
                                style: const TextStyle(
                                  fontWeight: FontWeight.w700,
                                  fontSize: 13,
                                ),
                              ),
                            ),
                            Tag(
                              firstNonEmpty([right['category'], 'Right']),
                              color: AppColors.info,
                            ),
                          ],
                        ),
                        if (asString(right['citizen_explanation'])
                            .isNotEmpty) ...[
                          const SizedBox(height: 6),
                          Text(
                            asString(right['citizen_explanation']),
                            style: const TextStyle(
                              fontSize: 12.5,
                              height: 1.45,
                            ),
                          ),
                        ],
                        if (asString(right['relevance_to_facts'])
                            .isNotEmpty) ...[
                          const SizedBox(height: 6),
                          Text(
                            'Why it applies: ${right['relevance_to_facts']}',
                            style: const TextStyle(
                              fontSize: 12,
                              color: AppColors.muted,
                              height: 1.4,
                            ),
                          ),
                        ],
                        if (asString(right['remedy_available']).isNotEmpty) ...[
                          const SizedBox(height: 6),
                          Text(
                            asString(right['remedy_available']),
                            style: const TextStyle(
                              fontSize: 11.5,
                              color: AppColors.teal,
                              height: 1.4,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
            ],
            if (asMapList(_result!['recommended_remedies']).isNotEmpty) ...[
              const SizedBox(height: 10),
              const SectionTitle('Recommended remedies'),
              AppCard(
                child: BulletList(
                  asMapList(_result!['recommended_remedies'])
                      .map((e) => asString(e))
                      .where((e) => e.isNotEmpty)
                      .toList(),
                  numbered: true,
                ),
              ),
            ],
            const SizedBox(height: 10),
            Text(
              asString(_result!['disclaimer']),
              style: const TextStyle(
                fontSize: 10.5,
                color: AppColors.muted,
                height: 1.4,
              ),
            ),
          ],
          const SizedBox(height: 18),
          const SectionTitle('Fundamental rights reference'),
          FutureBuilder<List<Map<String, dynamic>>>(
            future: _rightsFuture,
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Center(
                  child: Padding(
                    padding: EdgeInsets.all(16),
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                );
              }
              final items = snapshot.data ?? const [];
              if (items.isEmpty) {
                return const AppCard(
                  child: Text(
                    'Rights reference is unavailable.',
                    style: TextStyle(color: AppColors.muted),
                  ),
                );
              }
              return Column(
                children: [
                  for (final right in items)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 7),
                      child: AppCard(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '${firstNonEmpty([right['article'], ''])} · ${firstNonEmpty([right['title'], ''])}',
                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                                fontSize: 12.5,
                              ),
                            ),
                            const SizedBox(height: 3),
                            Text(
                              firstNonEmpty([right['explanation'], '']),
                              style: const TextStyle(
                                fontSize: 11.5,
                                color: AppColors.muted,
                                height: 1.4,
                              ),
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
    );
  }
}

// ---------------------------------------------------------------------------
// Authority finder
// ---------------------------------------------------------------------------

class AuthorityFinderScreen extends StatefulWidget {
  const AuthorityFinderScreen({super.key});

  @override
  State<AuthorityFinderScreen> createState() => _AuthorityFinderScreenState();
}

class _AuthorityFinderScreenState extends State<AuthorityFinderScreen> {
  final _issue = TextEditingController();
  String? _category;
  bool _judicial = false;
  bool _busy = false;
  String? _error;
  Map<String, dynamic>? _statutory;
  Map<String, dynamic>? _caseLaw;

  static const _categories = [
    'Consumer',
    'Cyber',
    'Property',
    'Labour',
    'RTI',
    'Family',
    'Criminal',
    'Tax',
  ];

  @override
  void dispose() {
    _issue.dispose();
    super.dispose();
  }

  Future<void> _find() async {
    if (_issue.text.trim().length < 3) {
      setState(() {
        _error = 'Describe the issue or grievance.';
      });
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final api = context.read<ApiService>();
      if (_judicial) {
        final result = await api.recommendAuthorities(_issue.text.trim());
        if (mounted) {
          setState(() {
            _caseLaw = result;
          });
        }
      } else {
        final result = await api.recommendStatutoryAuthority({
          'issue_description': _issue.text.trim(),
          'category': _category,
          'state_or_ut': 'All India',
          'is_urgent': false,
        });
        if (mounted) {
          setState(() {
            _statutory = result;
          });
        }
      }
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
    return Scaffold(
      appBar: AppBar(title: const Text('Authority finder')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 30),
        children: [
          SegmentedButton<bool>(
            segments: const [
              ButtonSegment(value: false, label: Text('Where to file')),
              ButtonSegment(value: true, label: Text('Case law')),
            ],
            selected: {_judicial},
            onSelectionChanged: (values) =>
                setState(() => _judicial = values.first),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _issue,
            minLines: 3,
            maxLines: 6,
            decoration: const InputDecoration(
              labelText: 'Issue or grievance *',
              alignLabelWithHint: true,
            ),
          ),
          if (!_judicial) ...[
            const SizedBox(height: 10),
            DropdownButtonFormField<String>(
              initialValue: _category,
              decoration: const InputDecoration(
                labelText: 'Category (optional)',
              ),
              items: [
                const DropdownMenuItem(value: null, child: Text('Not sure')),
                for (final category in _categories)
                  DropdownMenuItem(value: category, child: Text(category)),
              ],
              onChanged: (value) => setState(() => _category = value),
            ),
          ],
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: _busy ? null : _find,
            icon: _busy
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Icon(Icons.account_balance),
            label: Text(
              _busy
                  ? 'Searching…'
                  : (_judicial ? 'Find judgments' : 'Find authority'),
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 10),
            Text(
              _error!,
              style: const TextStyle(color: AppColors.danger, fontSize: 12),
            ),
          ],
          if (!_judicial && _statutory != null) ...[
            const SizedBox(height: 16),
            _statutoryResult(_statutory!),
          ],
          if (_judicial && _caseLaw != null) ...[
            const SizedBox(height: 16),
            _caseLawResult(_caseLaw!),
          ],
        ],
      ),
    );
  }

  Widget _statutoryResult(Map<String, dynamic> data) {
    final primary = asMap(data['primary_authority']);
    final alternatives = asMapList(data['alternative_authorities']);
    if (primary.isEmpty) {
      return AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              firstNonEmpty([
                data['detail'],
                'No authority matched this issue.',
              ]),
              style: const TextStyle(fontSize: 12.5, height: 1.4),
            ),
          ],
        ),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                firstNonEmpty([primary['name'], 'Authority']),
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
                  Tag(firstNonEmpty([primary['authority_type'], 'Authority'])),
                  Tag(
                    firstNonEmpty([primary['jurisdiction_level'], '']),
                    color: AppColors.info,
                  ),
                ],
              ),
              const SizedBox(height: 10),
              InfoRow(
                'Statutory basis',
                firstNonEmpty([primary['statutory_basis'], '—']),
              ),
              if (asString(primary['filing_procedure']).isNotEmpty) ...[
                const SizedBox(height: 6),
                Text(
                  asString(primary['filing_procedure']),
                  style: const TextStyle(fontSize: 12.5, height: 1.45),
                ),
              ],
            ],
          ),
        ),
        if (asString(primary['official_portal']).isNotEmpty) ...[
          const SizedBox(height: 8),
          ExternalLinkButton(
            url: asString(primary['official_portal']),
            label: 'Open portal',
          ),
        ],
        if (asMapList(data['escalation_hierarchy']).isNotEmpty) ...[
          const SizedBox(height: 12),
          const SectionTitle('Escalation path'),
          AppCard(
            child: BulletList(
              asMapList(data['escalation_hierarchy'])
                  .map((e) => asString(e))
                  .where((e) => e.isNotEmpty)
                  .toList(),
              numbered: true,
            ),
          ),
        ],
        if (alternatives.isNotEmpty) ...[
          const SizedBox(height: 12),
          const SectionTitle('Alternative authorities'),
          for (final authority in alternatives)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      firstNonEmpty([authority['name'], 'Authority']),
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 12.5,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      firstNonEmpty([authority['statutory_basis'], '']),
                      style: const TextStyle(
                        fontSize: 11,
                        color: AppColors.muted,
                        height: 1.4,
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
        if (asString(data['reasoning']).isNotEmpty) ...[
          const SizedBox(height: 10),
          Text(
            asString(data['reasoning']),
            style: const TextStyle(
              fontSize: 11,
              color: AppColors.muted,
              height: 1.4,
            ),
          ),
        ],
      ],
    );
  }

  Widget _caseLawResult(Map<String, dynamic> data) {
    final items = asMapList(data['recommendations']);
    if (items.isEmpty) {
      return AppCard(
        child: Text(
          'No verified judicial authorities matched this issue (${firstNonEmpty([data['source_status'], 'NOT IN SOURCE'])}). '
          'Vidhik does not generate or fabricate judgments.',
          style: const TextStyle(
            fontSize: 12.5,
            height: 1.45,
            color: AppColors.muted,
          ),
        ),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          '${asInt(data['total'], items.length)} verified authorities',
          style: const TextStyle(fontSize: 12, color: AppColors.muted),
        ),
        const SizedBox(height: 8),
        for (final item in items)
          Padding(
            padding: const EdgeInsets.only(bottom: 9),
            child: AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    firstNonEmpty([item['case_name'], 'Judgment']),
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 13.5,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    [
                      firstNonEmpty([item['court'], '']),
                      if (asString(item['judgment_date']).isNotEmpty)
                        formatDate(item['judgment_date']),
                      firstNonEmpty([item['citation'], '']),
                    ].where((e) => e.isNotEmpty).join(' · '),
                    style: const TextStyle(fontSize: 11, color: AppColors.teal),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    firstNonEmpty([item['legal_proposition'], '']),
                    style: const TextStyle(fontSize: 12.5, height: 1.45),
                  ),
                  if (asString(item['reason']).isNotEmpty) ...[
                    const SizedBox(height: 5),
                    Text(
                      asString(item['reason']),
                      style: const TextStyle(
                        fontSize: 11,
                        color: AppColors.muted,
                        height: 1.4,
                      ),
                    ),
                  ],
                  const SizedBox(height: 6),
                  Tag(
                    'Relevance ${(asDouble(item['relevance_score']) * 100).toStringAsFixed(0)}%',
                    color: AppColors.accent,
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Complaint / FIR generator
// ---------------------------------------------------------------------------

class ComplaintGeneratorScreen extends StatefulWidget {
  const ComplaintGeneratorScreen({super.key});

  @override
  State<ComplaintGeneratorScreen> createState() =>
      _ComplaintGeneratorScreenState();
}

class _ComplaintGeneratorScreenState extends State<ComplaintGeneratorScreen> {
  final _name = TextEditingController();
  final _contact = TextEditingController();
  final _address = TextEditingController();
  final _description = TextEditingController();
  final _date = TextEditingController();
  final _time = TextEditingController();
  final _location = TextEditingController();
  final _policeStation = TextEditingController();
  final _jurisdiction = TextEditingController();
  final _accused = TextEditingController();
  final _evidence = TextEditingController();
  final _loss = TextEditingController();
  final _injuries = TextEditingController();
  final _threats = TextEditingController();
  final _relief = TextEditingController();

  String _type = 'police_fir_request';
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    final auth = context.read<AuthProvider>().user;
    _name.text = auth?.fullName ?? '';
    _contact.text = auth?.phone ?? auth?.email ?? '';
    _jurisdiction.text = 'Pune, Maharashtra';
  }

  @override
  void dispose() {
    for (final controller in [
      _name,
      _contact,
      _address,
      _description,
      _date,
      _time,
      _location,
      _policeStation,
      _jurisdiction,
      _accused,
      _evidence,
      _loss,
      _injuries,
      _threats,
      _relief,
    ]) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<void> _generate() async {
    final required = {
      'Complainant name': _name.text,
      'Contact': _contact.text,
      'Address': _address.text,
      'Incident description': _description.text,
      'Incident date': _date.text,
      'Incident location': _location.text,
      'Jurisdiction': _jurisdiction.text,
    };
    final missing = required.entries
        .where((entry) => entry.value.trim().length < 2)
        .map((entry) => entry.key)
        .toList();
    if (missing.isNotEmpty) {
      setState(() {
        _error = 'Complete: ${missing.join(', ')}.';
      });
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final language = context.read<SettingsProvider>().language;
      final result = await context.read<ApiService>().generateComplaint({
        'complaint_type': _type,
        'complainant_name': _name.text.trim(),
        'complainant_contact': _contact.text.trim(),
        'complainant_address': _address.text.trim(),
        'incident_description': _description.text.trim(),
        'incident_date': _date.text.trim(),
        'incident_time': _time.text.trim().isEmpty ? null : _time.text.trim(),
        'incident_location': _location.text.trim(),
        'police_station_name': _policeStation.text.trim().isEmpty
            ? null
            : _policeStation.text.trim(),
        'jurisdiction_city_state': _jurisdiction.text.trim(),
        'accused_details': _accused.text.trim().isEmpty
            ? null
            : [
                {'name': null, 'description': _accused.text.trim()},
              ],
        'evidence_list': _evidence.text.trim().isEmpty
            ? null
            : _evidence.text
                  .split(',')
                  .map((e) => e.trim())
                  .where((e) => e.isNotEmpty)
                  .toList(),
        'financial_loss_amount': double.tryParse(_loss.text.trim()),
        'injuries_sustained': _injuries.text.trim().isEmpty
            ? null
            : _injuries.text.trim(),
        'threats_received': _threats.text.trim().isEmpty
            ? null
            : _threats.text.trim(),
        'requested_relief': _relief.text.trim().isEmpty
            ? null
            : _relief.text.trim(),
        'language': language,
      });
      if (!mounted) return;
      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => ComplaintResultScreen(result: result),
        ),
      );
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
    return Scaffold(
      appBar: AppBar(title: const Text('Complaint / FIR draft')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 30),
        children: [
          const AppCard(
            child: Text(
              'Drafts a factual complaint or FIR request for police filing. It does not register an FIR and does not '
              'assert that an offence is proven. The police decide registration under BNSS, 2023.',
              style: TextStyle(
                fontSize: 12,
                color: AppColors.muted,
                height: 1.45,
              ),
            ),
          ),
          const SizedBox(height: 12),
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(
                value: 'police_fir_request',
                label: Text('FIR request'),
              ),
              ButtonSegment(
                value: 'police_nc_complaint',
                label: Text('NC complaint'),
              ),
            ],
            selected: {_type},
            onSelectionChanged: (values) =>
                setState(() => _type = values.first),
          ),
          const SizedBox(height: 12),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Text(
                _error!,
                style: const TextStyle(
                  color: AppColors.danger,
                  fontSize: 12,
                  height: 1.4,
                ),
              ),
            ),
          TextField(
            controller: _name,
            decoration: const InputDecoration(labelText: 'Complainant name *'),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _contact,
            decoration: const InputDecoration(
              labelText: 'Contact number or email *',
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _address,
            minLines: 2,
            maxLines: 3,
            decoration: const InputDecoration(labelText: 'Postal address *'),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _description,
            minLines: 5,
            maxLines: 10,
            textCapitalization: TextCapitalization.sentences,
            decoration: const InputDecoration(
              labelText: 'Incident description * (at least 20 characters)',
              alignLabelWithHint: true,
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _date,
                  decoration: const InputDecoration(
                    labelText: 'Incident date *',
                    hintText: 'YYYY-MM-DD',
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: TextField(
                  controller: _time,
                  decoration: const InputDecoration(labelText: 'Time'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _location,
            decoration: const InputDecoration(labelText: 'Incident location *'),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _policeStation,
            decoration: const InputDecoration(labelText: 'Police station'),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _jurisdiction,
            decoration: const InputDecoration(
              labelText: 'City, district & state *',
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _accused,
            minLines: 2,
            maxLines: 4,
            decoration: const InputDecoration(
              labelText: 'Accused details / description (optional)',
              alignLabelWithHint: true,
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _evidence,
            decoration: const InputDecoration(
              labelText: 'Evidence (optional)',
              hintText: 'CCTV, medical report, receipts — comma separated',
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _loss,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(
              labelText: 'Financial loss (₹, optional)',
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _injuries,
            minLines: 2,
            maxLines: 3,
            decoration: const InputDecoration(
              labelText: 'Injuries sustained (optional)',
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _threats,
            minLines: 2,
            maxLines: 3,
            decoration: const InputDecoration(
              labelText: 'Threats received (optional)',
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _relief,
            minLines: 2,
            maxLines: 3,
            decoration: const InputDecoration(
              labelText: 'Requested relief (optional)',
              alignLabelWithHint: true,
            ),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _busy ? null : _generate,
            icon: _busy
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Icon(Icons.description_outlined),
            label: Text(_busy ? 'Drafting…' : 'Generate draft'),
          ),
        ],
      ),
    );
  }
}

class ComplaintResultScreen extends StatelessWidget {
  const ComplaintResultScreen({super.key, required this.result});

  final Map<String, dynamic> result;

  Future<void> _shareDocx(BuildContext context) async {
    try {
      final download = await context.read<ApiService>().exportComplaintDocx(
        result,
      );
      await shareDownloadedBytes(
        bytes: download.bytes,
        filename: download.filename,
        subject: 'VIDHIK complaint draft',
      );
    } on Exception catch (e) {
      if (context.mounted) showErrorSnack(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final safety = firstNonEmpty([result['safety_status'], 'safe']);
    final draft = asString(result['plain_text_draft']);
    final provisions = asMapList(result['potentially_relevant_provisions']);
    final guidance = asMapList(result['procedural_guidance']);
    final emergency = asMap(result['emergency_guidance']);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Complaint draft'),
        actions: [
          IconButton(
            tooltip: 'Copy draft',
            onPressed: () {
              Clipboard.setData(ClipboardData(text: draft));
              showInfoSnack(context, 'Draft copied.');
            },
            icon: const Icon(Icons.copy),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 30),
        children: [
          if (safety != 'safe')
            Container(
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.danger.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                firstNonEmpty([
                  result['safety_message'],
                  'This request triggered a safety check and the draft may be limited.',
                ]),
                style: const TextStyle(
                  fontSize: 12,
                  color: AppColors.danger,
                  height: 1.45,
                ),
              ),
            ),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  firstNonEmpty([result['document_title'], 'Complaint']),
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  firstNonEmpty([result['subject_line'], '']),
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.muted,
                    height: 1.4,
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  firstNonEmpty([result['recipient_header'], '']),
                  style: const TextStyle(fontSize: 11.5, height: 1.4),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          AppCard(
            child: SelectableText(
              draft,
              style: const TextStyle(fontSize: 12.5, height: 1.6),
            ),
          ),
          if (provisions.isNotEmpty) ...[
            const SizedBox(height: 14),
            const SectionTitle('Potentially relevant provisions'),
            for (final provision in provisions)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${firstNonEmpty([provision['act_name'], 'Act'])} — Section ${firstNonEmpty([provision['section_number'], '—'])}',
                        style: const TextStyle(
                          fontWeight: FontWeight.w600,
                          fontSize: 12.5,
                        ),
                      ),
                      if (asString(provision['section_title']).isNotEmpty)
                        Text(
                          asString(provision['section_title']),
                          style: const TextStyle(
                            fontSize: 11,
                            color: AppColors.muted,
                          ),
                        ),
                      if (asString(provision['description']).isNotEmpty) ...[
                        const SizedBox(height: 5),
                        Text(
                          asString(provision['description']),
                          style: const TextStyle(fontSize: 12, height: 1.4),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
          ],
          if (guidance.isNotEmpty) ...[
            const SizedBox(height: 10),
            const SectionTitle('Filing guidance'),
            AppCard(
              child: BulletList(
                guidance
                    .map((e) => asString(e))
                    .where((e) => e.isNotEmpty)
                    .toList(),
                numbered: true,
              ),
            ),
          ],
          if (emergency.isNotEmpty) ...[
            const SizedBox(height: 10),
            AppCard(
              child: Text(
                asString(
                  emergency['message'],
                  'Emergency guidance is available from the helplines screen.',
                ),
                style: const TextStyle(fontSize: 12.5, color: AppColors.danger),
              ),
            ),
          ],
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: () => _shareDocx(context),
            icon: const Icon(Icons.download_outlined, size: 18),
            label: const Text('Download / share DOCX'),
          ),
          const SizedBox(height: 10),
          Text(
            asString(result['disclaimer']),
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

// ---------------------------------------------------------------------------
// Emergency helplines
// ---------------------------------------------------------------------------

class EmergencyScreen extends StatefulWidget {
  const EmergencyScreen({super.key});

  @override
  State<EmergencyScreen> createState() => _EmergencyScreenState();
}

class _EmergencyScreenState extends State<EmergencyScreen> {
  late Future<List<Map<String, dynamic>>> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<ApiService>().emergencyHelplines();
  }

  Future<void> _call(String number) async {
    final uri = Uri.parse('tel:${number.replaceAll(' ', '')}');
    final ok = await launchUrl(uri);
    if (!ok && mounted) {
      showInfoSnack(context, 'Dial $number on your phone.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Emergency helplines')),
      body: AsyncView<List<Map<String, dynamic>>>(
        future: _future,
        onRetry: () => setState(() {
          _future = context.read<ApiService>().emergencyHelplines();
        }),
        loadingText: 'Loading helplines…',
        builder: (context, helplines) {
          if (helplines.isEmpty) {
            return const EmptyState(
              title: 'Helplines unavailable',
              message: 'Call 112 for immediate police, fire or ambulance assistance.',
              icon: Icons.phone_disabled,
            );
          }
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 30),
            children: [
              Container(
                padding: const EdgeInsets.all(15),
                decoration: BoxDecoration(
                  color: AppColors.danger.withValues(alpha: 0.07),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: AppColors.danger.withValues(alpha: 0.25),
                  ),
                ),
                child: const Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.emergency, color: AppColors.danger),
                    SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'If there is immediate danger to life, call 112 now. Use these numbers for the purpose '
                        'described; they are staffed by government services.',
                        style: TextStyle(fontSize: 12, height: 1.45),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              for (final helpline in helplines)
                Padding(
                  padding: const EdgeInsets.only(bottom: 9),
                  child: AppCard(
                    child: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(9),
                          decoration: BoxDecoration(
                            color: AppColors.danger.withValues(alpha: 0.08),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: const Icon(
                            Icons.call,
                            color: AppColors.danger,
                            size: 19,
                          ),
                        ),
                        const SizedBox(width: 11),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                firstNonEmpty([helpline['name'], 'Helpline']),
                                style: const TextStyle(
                                  fontWeight: FontWeight.w600,
                                  fontSize: 13,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                firstNonEmpty([helpline['description'], '']),
                                style: const TextStyle(
                                  fontSize: 11,
                                  color: AppColors.muted,
                                  height: 1.35,
                                ),
                              ),
                              const SizedBox(height: 3),
                              Text(
                                firstNonEmpty([helpline['number'], '']),
                                style: const TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w700,
                                  color: AppColors.danger,
                                ),
                              ),
                            ],
                          ),
                        ),
                        IconButton.filled(
                          tooltip: 'Call',
                          onPressed: () =>
                              _call(firstNonEmpty([helpline['number'], ''])),
                          icon: const Icon(Icons.phone, size: 18),
                        ),
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
