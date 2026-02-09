#!/usr/bin/env python3
"""CLI tool for managing feature toggles."""

import asyncio
import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Optional

from database import db_manager
from services.feature_toggle_service import FeatureToggleService
from models.feature_toggle import FeatureScope, ToggleStatus, FeatureContext


async def check_feature(args):
    """Check if a feature is enabled."""
    service = FeatureToggleService(db_manager.service_client)
    
    context = FeatureContext(
        user_id=args.user_id,
        country_code=args.country_code,
        tier=args.tier
    )
    
    is_enabled = await service.is_feature_enabled(args.feature_name, context)
    
    print(f"Feature '{args.feature_name}' is {'ENABLED' if is_enabled else 'DISABLED'}")
    print(f"Context: {context.to_dict()}")


async def list_features(args):
    """List all features or enabled features for context."""
    service = FeatureToggleService(db_manager.service_client)
    
    if args.context:
        context = FeatureContext(
            user_id=args.user_id,
            country_code=args.country_code,
            tier=args.tier
        )
        
        enabled_features = await service.get_enabled_features(context)
        print(f"Enabled features for context {context.to_dict()}:")
        for feature in sorted(enabled_features):
            print(f"  - {feature}")
    else:
        # List all feature definitions
        result = db_manager.service_client.table("feature_definition").select("*").execute()
        
        if result.data:
            print("All feature definitions:")
            for feature in result.data:
                status = "ENABLED" if feature["default_enabled"] else "DISABLED"
                tier = f" (requires {feature['requires_tier']})" if feature["requires_tier"] else ""
                restricted = " [RESTRICTED]" if feature["regulatory_restricted"] else ""
                print(f"  - {feature['name']}: {status}{tier}{restricted}")
                print(f"    {feature['description']}")
        else:
            print("No feature definitions found")


async def update_toggle(args):
    """Update a feature toggle."""
    service = FeatureToggleService(db_manager.service_client)
    
    scope = FeatureScope(args.scope)
    status = ToggleStatus(args.status)
    
    expires_at = None
    if args.expires_at:
        expires_at = datetime.fromisoformat(args.expires_at).replace(tzinfo=timezone.utc)
    
    conditions = {}
    if args.conditions:
        conditions = json.loads(args.conditions)
    
    success = await service.update_feature_toggle(
        feature_name=args.feature_name,
        scope=scope,
        scope_value=args.scope_value,
        status=status,
        conditions=conditions,
        expires_at=expires_at
    )
    
    if success:
        print(f"Successfully updated feature toggle: {args.feature_name}")
    else:
        print(f"Failed to update feature toggle: {args.feature_name}")
        sys.exit(1)


async def get_country_config(args):
    """Get country configuration."""
    service = FeatureToggleService(db_manager.service_client)
    
    config = await service.get_country_config(args.country_code)
    
    if config:
        print(f"Country configuration for {args.country_code}:")
        print(f"  Name: {config.country_name}")
        print(f"  Currency: {config.currency_code}")
        print(f"  Timezone: {config.timezone}")
        print(f"  Locale: {config.locale}")
        print(f"  Payment Providers: {', '.join(config.payment_providers)}")
        print(f"  Active: {config.is_active}")
        if config.regulatory_restrictions:
            print(f"  Restrictions: {json.dumps(config.regulatory_restrictions, indent=2)}")
    else:
        print(f"Country configuration not found for {args.country_code}")
        sys.exit(1)


async def get_usage_stats(args):
    """Get feature usage statistics."""
    service = FeatureToggleService(db_manager.service_client)
    
    stats = await service.get_feature_usage_stats(
        feature_name=args.feature_name,
        country_code=args.country_code,
        days=args.days
    )
    
    if stats:
        print(f"Feature usage statistics (last {args.days} days):")
        for stat in stats:
            print(f"  Feature: {stat['feature_name']}")
            print(f"    User: {stat['user_id']}")
            print(f"    Country: {stat.get('country_code', 'N/A')}")
            print(f"    Usage Count: {stat['usage_count']}")
            print(f"    Last Used: {stat['last_used_at']}")
            print()
    else:
        print("No usage statistics found")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Feature Toggle Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Check feature command
    check_parser = subparsers.add_parser("check", help="Check if a feature is enabled")
    check_parser.add_argument("feature_name", help="Name of the feature to check")
    check_parser.add_argument("--user-id", type=int, help="User ID for context")
    check_parser.add_argument("--country-code", help="Country code for context")
    check_parser.add_argument("--tier", help="User tier for context")
    
    # List features command
    list_parser = subparsers.add_parser("list", help="List features")
    list_parser.add_argument("--context", action="store_true", help="Show enabled features for context")
    list_parser.add_argument("--user-id", type=int, help="User ID for context")
    list_parser.add_argument("--country-code", help="Country code for context")
    list_parser.add_argument("--tier", help="User tier for context")
    
    # Update toggle command
    update_parser = subparsers.add_parser("update", help="Update a feature toggle")
    update_parser.add_argument("feature_name", help="Name of the feature")
    update_parser.add_argument("scope", choices=["global", "country", "group", "user"], help="Toggle scope")
    update_parser.add_argument("--scope-value", help="Scope value (country code, group ID, user ID)")
    update_parser.add_argument("status", choices=["enabled", "disabled", "testing"], help="Toggle status")
    update_parser.add_argument("--conditions", help="JSON conditions for the toggle")
    update_parser.add_argument("--expires-at", help="Expiration date (ISO format)")
    
    # Country config command
    country_parser = subparsers.add_parser("country", help="Get country configuration")
    country_parser.add_argument("country_code", help="Country code (e.g., KE, US)")
    
    # Usage stats command
    stats_parser = subparsers.add_parser("stats", help="Get feature usage statistics")
    stats_parser.add_argument("--feature-name", help="Filter by feature name")
    stats_parser.add_argument("--country-code", help="Filter by country code")
    stats_parser.add_argument("--days", type=int, default=30, help="Number of days to look back")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Run the appropriate command
    if args.command == "check":
        asyncio.run(check_feature(args))
    elif args.command == "list":
        asyncio.run(list_features(args))
    elif args.command == "update":
        asyncio.run(update_toggle(args))
    elif args.command == "country":
        asyncio.run(get_country_config(args))
    elif args.command == "stats":
        asyncio.run(get_usage_stats(args))


if __name__ == "__main__":
    main()