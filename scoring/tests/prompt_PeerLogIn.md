Here is a simple unit test for the `PeerLogIn` function using the `testing` package in Go. This test checks that the `PeerLogIn` function correctly sets the `isLoggedIn` field to `true` and `sessionConnDirection` field to the provided `dir`.

```go
package metrics

import (
	"testing"
	"time"
)

func TestPeerLogIn(t *testing.T) {
	testTime := time.Now()
	testDir := PeerConnectionDirection("test_direction")

	testCounters := &Counters{}

	PeerLogIn(testTime, testDir)(testCounters)

	if testCounters.isLoggedIn != true {
		t.Errorf("PeerLogIn did not set isLoggedIn to true")
	}

	if testCounters.sessionConnDirection != testDir {
		t.Errorf("PeerLogIn did not set sessionConnDirection to %s", testDir)
	}
}
```

This test first creates a `Counters` struct and a `PeerConnectionDirection` value. It then calls `PeerLogIn` with these values and checks that the `isLoggedIn` field is set to `true` and the `sessionConnDirection` field is set to the provided `dir`.

If the `isLoggedIn` field is not set to `true` or the `sessionConnDirection` field is not set to the provided `dir`, the test will fail and print an error message.
