# journey-test-on-the-agent-box (+ verify-causes-don't-hand-wave)
Run the real browser (Playwright) and real effects to verify the user-visible outcome on this box. Wait on the real signal, never a fixed sleep. A test passing only on retry is a must-investigate race. Don't ship a cause ("flaky", "timing") you haven't probed.
