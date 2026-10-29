import 'dart:io';

import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

/// Writes an authenticated backend export to a temporary file and opens the
/// native share sheet, so documents can be saved to the device, emailed or
/// sent to another app without exposing the session token.
Future<void> shareDownloadedBytes({
  required List<int> bytes,
  required String filename,
  String? subject,
}) async {
  final dir = await getTemporaryDirectory();
  final file = File('${dir.path}/$filename');
  await file.writeAsBytes(bytes, flush: true);
  await SharePlus.instance.share(
    ShareParams(
      files: [XFile(file.path)],
      subject: subject ?? filename,
      text: 'Exported from VIDHIK AI',
    ),
  );
}
