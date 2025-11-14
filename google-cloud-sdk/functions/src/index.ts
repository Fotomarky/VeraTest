import {onRequest} from "firebase-functions/v2/https";
import {onCall} from "firebase-functions/v2/https";
import * as logger from "firebase-functions/logger";
import * as admin from "firebase-admin";
import Stripe from "stripe";

// Initialize Firebase Admin SDK
admin.initializeApp();

// Initialize Stripe
// IMPORTANT: You must set this key in your environment
const stripeSecretKey = process.env.STRIPE_SECRET_KEY as string;
const stripe = new Stripe(stripeSecretKey, {
  apiVersion: "2025-04-10",
});

/**
 * Firebase Function to create a new Stripe Checkout session.
 * This is a "Callable Function" triggered by your React app.
 */
export const createStripeCheckout = onCall(async (request) => {
  // Check if user is authenticated
  if (!request.auth) {
    logger.error("User is not authenticated.");
    throw new Error("You must be logged in to make a purchase.");
  }

  const userId = request.auth.uid;
  const YOUR_DOMAIN = "https://your-website-url.com"; // TODO: Change this to your live URL

  try {
    const session = await stripe.checkout.sessions.create({
      payment_method_types: ["card"],
      line_items: [
        {
          price_data: {
            currency: "usd",
            product_data: {
              name: "Premium Access",
              description: "Unlock high-res, watermark-free images.",
            },
            unit_amount: 500, // Example: $5.00
          },
          quantity: 1,
        },
      ],
      mode: "payment",
      success_url: `${YOUR_DOMAIN}?payment=success`,
      cancel_url: `${YOUR_DOMAIN}?payment=cancel`,
      // Attach the Firebase User ID to the session's metadata
      metadata: {
        userId: userId,
      },
    });

    logger.info(`Stripe session created for user ${userId}`);
    return {id: session.id};
  } catch (error) {
    logger.error("Error creating Stripe session:", error);
    throw new Error("Failed to create Stripe session.");
  }
});

/**
 * Firebase Function to listen for the Stripe Webhook.
 * This is an "HTTP Request Function" triggered by Stripe.
 */
export const stripeWebhook = onRequest(async (req, res) => {
  if (!stripe) {
    logger.error("Stripe has not been initialized.");
    res.status(500).send("Internal server error.");
    return;
  }

  const signature = req.headers["stripe-signature"] as string;
  // IMPORTANT: You must set this key in your environment
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET as string;

  let event: Stripe.Event;

  try {
    event = stripe.webhooks.constructEvent(
      req.rawBody,
      signature,
      webhookSecret,
    );
  } catch (error) {
    logger.error("Webhook signature verification failed:", error);
    res.status(400).send(`Webhook Error: ${(error as Error).message}`);
    return;
  }

  // Handle the event
  if (event.type === "checkout.session.completed") {
    const session = event.data.object as Stripe.Checkout.Session;
    const userId = session.metadata?.userId;

    if (userId) {
      logger.info(`Payment successful for user ${userId}.`);
      await addPaidClaim(userId);
    }
  }

  res.json({received: true});
});

/**
 * Helper function to add the 'isPaid' custom claim to a user.
 */
async function addPaidClaim(userId: string): Promise<void> {
  const auth = admin.auth();
  try {
    const user = await auth.getUser(userId);
    const currentClaims = user.customClaims || {};

    // Set the new claim
    await auth.setCustomUserClaims(userId, {
      ...currentClaims,
      isPaid: true,
    });

    logger.info(`Custom claim 'isPaid' set to true for user ${userId}`);
  } catch (error) {
    logger.error(`Failed to set custom claim for user ${userId}`, error);
  }
}

/**
 * Import function triggers from their respective submodules:
 *
 * import {onCall} from "firebase-functions/v2/https";
 * import {onDocumentWritten} from "firebase-functions/v2/firestore";
 *
 * See a full list of supported triggers at https://firebase.google.com/docs/functions
 */

import {setGlobalOptions} from "firebase-functions";
import {onRequest} from "firebase-functions/https";
import * as logger from "firebase-functions/logger";

// Start writing functions
// https://firebase.google.com/docs/functions/typescript

// For cost control, you can set the maximum number of containers that can be
// running at the same time. This helps mitigate the impact of unexpected
// traffic spikes by instead downgrading performance. This limit is a
// per-function limit. You can override the limit for each function using the
// `maxInstances` option in the function's options, e.g.
// `onRequest({ maxInstances: 5 }, (req, res) => { ... })`.
// NOTE: setGlobalOptions does not apply to functions using the v1 API. V1
// functions should each use functions.runWith({ maxInstances: 10 }) instead.
// In the v1 API, each function can only serve one request per container, so
// this will be the maximum concurrent request count.
setGlobalOptions({ maxInstances: 10 });

// export const helloWorld = onRequest((request, response) => {
//   logger.info("Hello logs!", {structuredData: true});
//   response.send("Hello from Firebase!");
// });
