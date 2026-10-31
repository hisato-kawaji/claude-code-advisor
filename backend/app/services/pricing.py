"""User-configured rates in USD per million tokens; never represents a bill."""
from datetime import date


def estimate_entry(entry, settings):
    if settings.get('contract') != 'api':
        return None
    message = entry.get('message') or {}
    if not isinstance(message, dict):
        return None
    model, usage = message.get('model'), message.get('usage') or {}
    try:
        day = date.fromisoformat(entry['timestamp'][:10])
        candidates = [r for r in settings.get('rates', []) if r['model'] == model
                      and r['provider'] == settings.get('provider')
                      and date.fromisoformat(r['valid_from']) <= day
                      and (not r.get('valid_until') or day <= date.fromisoformat(r['valid_until']))]
        # Ambiguous overlapping prices must never silently pick one.
        if len(candidates) != 1:
            return None
        rate = candidates[0]
        inp, out, read, written = (int(usage.get(k) or 0) for k in
            ('input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'))
        creation = usage.get('cache_creation') or {}
        short = int(creation.get('ephemeral_5m_input_tokens') or 0)
        long = int(creation.get('ephemeral_1h_input_tokens') or 0)
        if min(inp, out, read, written, short, long) < 0 or short + long != written:
            return None
        return (inp * rate['input'] + out * rate['output'] + read * rate['cache_read'] +
                short * rate['cache_write_5m'] + long * rate['cache_write_1h']) / 1_000_000
    except (KeyError, TypeError, ValueError):
        return None
