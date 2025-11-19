def sanitize_filename(s: str) -> str:
    return ''.join(c for c in s if c.isalnum() or c in "-_.() ")

## Example usage
unsafe_str = 'fo|o-b|&ar$cls#baz?qux@127/\\9]'
print('unsafe :', unsafe_str)
safe_filename = sanitize_filename(unsafe_str)
print('safe   :', safe_filename)  # Output: 'foobarqux1279'