Here is a simple test for the `MatchCaptureGroups` function:

```go
package stringutil

import (
	"regexp"
	"testing"
)

func TestMatchCaptureGroups(t *testing.T) {
	regEx, _ := regexp.Compile("(foo)")
	str := "foobar"
	expected := map[string]string{
		"foo": "foo",
	}
	result := MatchCaptureGroups(regEx, str)

	if len(result) != len(expected) {
		t.Errorf("Expected %v, but got %v", expected, result)
	}

	for key, value := range expected {
		if result[key] != value {
			t.Errorf("Expected %v for key %v, but got %v", value, key, result[key])
		}
	}
}
```

This test checks if the function correctly identifies the named capture groups in the string. It compares the expected result with the actual result, and if they are not equal, it reports an error.

Please note that the error message is just a simple error message, and you can customize it according to your needs.

Also, please note that the `regexp.Compile` function returns a `*Regexp`, which is a pointer to a `Regexp`. The `_` in the `_, err := regexp.Compile("(foo)")` is a common idiom in Go to ignore the result of `Compile`, which is not used in this case.

