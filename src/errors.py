"""Controlled error categories; raw provider messages are never displayed."""


def reason_error(reason):
    error = RuntimeError(reason)
    error.subtitler_reason = reason
    return error


def classify_error(error):
    reason = getattr(error, 'subtitler_reason', '')
    if reason in ('content_blocked', 'output_truncated', 'invalid_translation_response',
                  'missing_word_timestamps', 'missing_translation_key'):
        return reason
    if reason.startswith('model_unavailable'):
        return 'model_unavailable'
    if 'timestamp' in reason or reason == 'non_positive_duration':
        return 'invalid_timestamps'
    code = str(getattr(error, 'code', None) or getattr(error, 'status_code', ''))
    status = {'429':'quota','401':'authentication','403':'authentication',
              '404':'model_unavailable','400':'invalid_request',
              '500':'service_unavailable','502':'service_unavailable',
              '503':'service_unavailable','504':'service_unavailable'}
    if code in status:
        return status[code]
    message = str(error).lower()  # inspection only, never display or persist
    if 'quota' in message or 'resource_exhausted' in message:
        return 'quota'
    if 'timeout' in message or 'timed out' in message or isinstance(error, TimeoutError):
        return 'timeout'
    if 'connection' in message:
        return 'service_unavailable'
    return 'unknown'


def response_reason(response):
    value = lambda x: str(getattr(x, 'value', x) or '').upper().split('.')[-1]
    blocked = getattr(getattr(response, 'prompt_feedback', None), 'block_reason', None)
    if value(blocked) not in ('', '0', 'BLOCK_REASON_UNSPECIFIED'):
        return 'content_blocked'
    for candidate in getattr(response, 'candidates', None) or []:
        finish = value(getattr(candidate, 'finish_reason', None))
        if finish in ('SAFETY', 'BLOCKLIST', 'PROHIBITED_CONTENT', 'SPII', 'RECITATION', 'IMAGE_SAFETY'):
            return 'content_blocked'
        if finish == 'MAX_TOKENS':
            return 'output_truncated'
    return None
