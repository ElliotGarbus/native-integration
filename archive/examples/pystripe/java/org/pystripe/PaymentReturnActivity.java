// Illustrative. A real wheel ships a working class; this repository ships one
// that is real enough to be checked — its path and its `package` both fall
// under `org.pystripe`, which is the namespace the sidecar claims, and §6.1
// rule 1 is what that satisfies.
//
// The activity exists because Stripe's 3D Secure flow returns through the
// browser rather than through the SDK, so something in the application's
// manifest has to receive the redirect. It is exported for the same reason,
// which is why the sidecar declares `reason` and the application has to
// approve it: an exported activity is reachable by any application on the
// device, and no producer gets to decide that on the application's behalf.

package org.pystripe;

import android.app.Activity;
import android.os.Bundle;

public final class PaymentReturnActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // A real implementation hands the redirect URI to the Stripe SDK and
        // finishes. There is nothing here worth pretending to.
        finish();
    }
}
