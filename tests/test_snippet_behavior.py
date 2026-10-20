"""Behavior of snippets that carry logic beyond compiling: webhook signature verification."""

import ast
import hashlib
import hmac
import json
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

REFS = Path(__file__).resolve().parent.parent / "skills/hypertrack-integration/references"
SECRET = "s3cret"
BODY = b'[{"type":"order","data":{"value":"arrived","order_handle":"o1"},"recorded_at":"2026-11-03T15:52:10.000Z"}]'
SIGNATURE = hmac.new(SECRET.encode(), BODY, hashlib.sha1).hexdigest()


def fence(markdown_file, language, index=0):
    blocks = re.findall(rf"^```{language}\n(.*?)^```", (REFS / markdown_file).read_text(), re.M | re.S)
    return blocks[index]


class PythonWebhookSignatureTest(unittest.TestCase):
    def setUp(self):
        module = ast.parse(fence("webhooks.md", "python"))
        function = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "valid_signature")
        namespace = {"hashlib": hashlib, "hmac": hmac}
        exec(compile(ast.Module(body=[function], type_ignores=[]), "webhooks.md", "exec"), namespace)
        self.valid_signature = namespace["valid_signature"]

    def test_accepts_hmac_sha1_of_raw_body(self):
        self.assertTrue(self.valid_signature(BODY, SIGNATURE, SECRET))

    def test_rejects_wrong_missing_and_reserialized(self):
        self.assertFalse(self.valid_signature(BODY, "0" * 40, SECRET))
        self.assertFalse(self.valid_signature(BODY, None, SECRET))
        reserialized = json.dumps(json.loads(BODY)).encode()  # adds spaces: must not verify
        self.assertFalse(self.valid_signature(reserialized, SIGNATURE, SECRET))


class NodeWebhookSignatureTest(unittest.TestCase):
    def test_express_snippet_signature_check(self):
        self.assertTrue(shutil.which("node"), "node is required to test the Express snippet")
        with tempfile.TemporaryDirectory() as tmp:
            express = Path(tmp, "node_modules/express")
            express.mkdir(parents=True)
            (express / "index.js").write_text(
                "function express() { return { post() {} }; }\nexpress.raw = () => () => {};\nmodule.exports = express;\n"
            )
            Path(tmp, "snippet.js").write_text(fence("webhooks.md", "js") + "\nmodule.exports = { validSignature };\n")
            script = textwrap.dedent(f"""
                const {{ validSignature }} = require('./snippet.js');
                const body = Buffer.from({json.dumps(BODY.decode())});
                console.log(JSON.stringify([
                  validSignature(body, '{SIGNATURE}', '{SECRET}'),
                  validSignature(body, '{"0" * 40}', '{SECRET}'),
                  validSignature(body, undefined, '{SECRET}'),
                  validSignature(body, 'short', '{SECRET}'),
                ]));
            """)
            result = subprocess.run(["node", "-e", script], cwd=tmp, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [True, False, False, False])


if __name__ == "__main__":
    unittest.main()
