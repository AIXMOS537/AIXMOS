# Domain Architecture

## Recommended Setup

Use `allinonemanagementsolutions.com` as the corporate parent domain.

Use `tmmtrentals.com` as the customer-facing rental brand.

Use `.net` domains as redirects or backup infrastructure:

- `allinonemanagementsolutions.net` redirects to `allinonemanagementsolutions.com`
- `tmmtrentals.net` redirects to `tmmtrentals.com`

## Suggested Subdomains

### All In One Management Solutions

- `www.allinonemanagementsolutions.com` - public website
- `portal.allinonemanagementsolutions.com` - client portal
- `admin.allinonemanagementsolutions.com` - internal admin dashboard
- `training.allinonemanagementsolutions.com` - staff training portal
- `partners.allinonemanagementsolutions.com` - partner intake and partner resources

### TMMT Rentals

- `www.tmmtrentals.com` - rental website
- `apply.tmmtrentals.com` - rental application
- `fleet.tmmtrentals.com` - fleet partner intake
- `portal.tmmtrentals.com` - renter/customer portal

## Brand Separation

All In One Management Solutions should feel like the corporate/financial services company.

TMMT Rentals should feel like the vehicle rental and fleet operations company.

The admin dashboard can manage both brands from one backend.

## Recommended First Version

Start with one codebase and one backend:

- `/` - All In One public site
- `/rentals` - TMMT public site
- `/admin` - internal admin
- `/portal` - client portal
- `/training` - staff training

Later, split into separate apps or subdomains when traffic and operations justify it.
