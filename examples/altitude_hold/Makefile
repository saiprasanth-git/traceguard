# Build and verify the ALTH example, then gate on requirements traceability.

CC      ?= gcc
CFLAGS  ?= -std=c99 -Wall -Wextra -Werror -Wpedantic -O2 -Iinclude -Itests
LDLIBS  ?= -lm
BUILD   := build

SRC     := src/altitude_hold.c
TEST    := tests/test_altitude_hold.c
BIN     := $(BUILD)/test_altitude_hold

.PHONY: all test trace report clean

all: test trace

$(BUILD):
	mkdir -p $(BUILD)

$(BIN): $(SRC) $(TEST) include/altitude_hold.h tests/unity_min.h | $(BUILD)
	$(CC) $(CFLAGS) $(SRC) $(TEST) -o $@ $(LDLIBS)

## Run the verification suite.
test: $(BIN)
	./$(BIN)

## Fail if any requirement is untraced, unimplemented or unverified.
trace:
	traceguard check --root .

## Emit markdown, HTML and JSON traceability artefacts into build/.
report: | $(BUILD)
	traceguard report --root . --format markdown -o $(BUILD)/traceability.md
	traceguard report --root . --format html     -o $(BUILD)/traceability.html
	traceguard report --root . --format json     -o $(BUILD)/traceability.json

clean:
	rm -rf $(BUILD)
