# Marketing source suggestions

Marketing analytics suggests connecting an ad platform when a matching UTM source has events with paid attribution signals.
Connection suggestions display the number of these events over the last seven days and rank platforms by that count.
Events without paid signals and fuzzy-only source matches do not increase the count.
Each event counts at most once for its matched platform, even if it carries multiple paid signals.

The count includes all matching event types, so it does not represent unique visitors or ad clicks.
For example, a source with 700 matching events, including 17 with paid signals, shows 17 events in its connection suggestion.
It ranks below a source with 25 paid events, regardless of that source's total traffic.

These counts guide connection suggestions; they do not change report attribution or connected-source sync checks.

## Search performance

Spend and conversions require a synced ad platform source in the current search filters.
Google Search Console reports organic traffic metrics only.
When no paid source is ready, the disabled control directs users to check their source settings or filters.
For Google Ads landing pages, enable `landing_page_stats` and wait for its first sync to finish.

## X Ads

X Ads uses `twitter`, `x`, `twitter_ads`, and `x_ads` as its default source aliases.
The `marketing-analytics-twitter-ads` flag controls availability in Marketing analytics, independently of the warehouse connector's `dwh-twitter-ads` release flag.
When the Marketing analytics flag is off, X Ads is excluded from native reporting, connection menus, and health diagnostics, including attribution suggestions.
Report UTM normalization stays stable across flag changes, as it does for the other native integrations.
The connector retains its existing OAuth setup requirements.
The new-source announcement uses the shared dismissal key: adding X Ads does not show it again to users who already opened the announcement.

Import `campaigns` and `campaign_stats` for campaign reporting, and `line_items` and `line_item_stats` for ad group reporting.
All four tables are recommended and selected by default when setting up a new X Ads source.
Existing connections keep their selected tables until the user changes them.
Daily spend is converted from micros using each row's funding-instrument currency and report date.
Monetary tiles require the currency column; impressions remain available when only currency is missing.
Clicks include the engagement clicks reported by X, not only outbound link clicks.
The current import provides spend, clicks, and impressions; platform-reported conversions and revenue are not imported.
PostHog conversion goals still work through campaign attribution.
Ad-level reporting is unavailable because the connector does not import promoted-post statistics.

## Bing Ads landing pages

Search performance includes Bing Ads in the Landing pages view.
Enable `destination_url_performance_report` in the Bing Ads source settings and wait for its first successful sync.
The view groups search distribution metrics by destination URL and currency, with clicks, impressions, spend, and platform-attributed conversions.
The connector uses `ConversionsQualified` because Microsoft deprecated `Conversions` for this report.
Keyword reporting continues to use `keyword_performance_report`.

## Source onboarding

Marketing analytics skips source onboarding when a marketing source is configured, including sources whose first sync is still running.
For projects without sources, onboarding scans UTM-tagged events and suggests matching ad platforms.
Users can continue to the dashboard at any time, connect more platforms while a sync runs, or choose from all supported sources when no platform is detected.
The event scan is cached for seven days per project and lookback window; source connection and sync health continue to use current configuration.
Use **Scan events again** in Setup → Sources to bypass the event cache.
The dashboard keeps pending source suggestions and sync status visible so missing spend data is not mistaken for zero spend.
Conversion goals are configured within the product rather than as an onboarding step.

The source onboarding shows only the scan while it runs, then only the detected platforms.
**Skip and add manually** opens the complete source selector at any time, including while the scan runs.
The scan message states its seven-day detection window.

On the current dashboard, spend and ad performance tiles stay hidden until a source supplies data.
The connection notice or detected-source suggestions explain what needs to be connected.

Source health refreshes on window focus without replacing the resolved dashboard or cached event suggestions with a loading screen.
The initial source check uses a compact loading state; projects without sources show a connection card instead of empty metric placeholders.

Source setup uses a consistent panel for connection checks, event scanning, suggestions, empty results, and recoverable errors.
Detected platforms show concise evidence with expandable details.
Configured connections show their first-sync status beside pending platforms.
The manual catalog supports search and returning to suggestions.
The current dashboard shows metric filters only once marketing data is available; beta feedback is available in the scene header.

Source setup panels are centered within the scene.
**Browse integrations** opens the searchable catalog in place; **Back to suggestions** restores the pending connections without another scan.
When `marketing-analytics-organic-keywords` enables Search performance, setup and the manual catalog show Google Search Console as an optional organic-search connection, separate from detected ad platforms.

The source setup panel explains how connections centralize campaign performance and how conversion goals based on PostHog events measure conversion costs and return on ad spend.
When Search performance is enabled, it also explains paid-keyword and organic-query analysis for optimizing search ads.
Pending-source cards offer the source connection buttons and **Browse integrations**; they do not redirect users to Setup to review the same suggestions.

Manual event scans are available from onboarding and the dashboard with **Scan again**.
A successful scan starts a one-hour cooldown per project; the server also reuses the scan during this cooldown.
Failed scans can be retried. Suggested connections stay visible during a refresh.
When no platforms are detected, the panel explains how UTM parameters on ad links help PostHog identify platforms.

With Search performance enabled, a connected Google Search Console source also skips onboarding.
The current dashboard shows Search performance below a compact ad-source connection panel when no ad data is ready.
Search Console does not unlock ad spend metrics; its sync and data readiness remain independent.

The Search Console connection card explains how connecting Google Ads adds paid keyword, spend, and conversion data alongside organic search queries.

When neither Google Ads nor Google Search Console is connected, the enabled Search performance flag shows a separate search connection card with both integrations.

Search connections appear as a separate card below both the source suggestions and the manual integration catalog.

The integration catalog opened inside the dashboard has no continue action because the user is already on the dashboard.
The initial onboarding catalog offers **Skip for now** when no sources are connected.
