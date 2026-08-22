'use strict';

const { execFile } = require('child_process');

const SCRIPT = `
on run {targetAddr, targetText}
  tell application "Messages"
    try
      set svc to 1st service whose service type = iMessage
      set theBuddy to buddy targetAddr of svc
      send targetText to theBuddy
      return "imessage"
    on error
      set smsService to 1st service whose service type = SMS
      set theBuddy to buddy targetAddr of smsService
      send targetText to theBuddy
      return "sms"
    end try
  end tell
end run
`;

function sendViaMessages(to, text) {
  return new Promise((resolve, reject) => {
    const dest = String(to || '').trim();
    const body = String(text || '').trim();
    if (!dest || !body) return reject(new Error('to and text required'));
    execFile('osascript', ['-e', SCRIPT, dest, body], { timeout: 20000 }, (err, stdout, stderr) => {
      if (err) return reject(new Error((stderr || err.message || '').trim()));
      resolve({ ok: true, via: (stdout || '').trim() || 'imessage' });
    });
  });
}

module.exports = { sendViaMessages };
