some text before
```go
package markdown

import (
	"testing"
)

func TestToHTML(t *testing.T) {
	testCases := []struct {
		name     string
		input    string
		expected string
	}{
		{
			name:     "simple markdown",
			input:    "# Hello World\n\nThis is some markdown.",
			expected: "<h1>Hello World</h1>\n\n<p>This is some markdown.</p>\n"
		},
		{
			name:     "complex markdown",
			input:    "# Hello World\n\nThis is a [link](https://example.com).\n\nAnd another one.",
			expected: "<h1>Hello World</h1>\n\n<p>This is a <a href=\"https://example.com.\">link</a>.</p>\n\n<p>And another one.</p>\n",
		},
		// Add more test cases as needed
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			html, err := ToHTML([]byte(tc.input))
			if err != nil {
				t.Errorf("ToHTML failed: %v", err)
			}

			if string(html) != tc.expected {
				t.Errorf("Expected %s, got %s", tc.expected, string(html))
			}
		})
	}
}
```
some text after