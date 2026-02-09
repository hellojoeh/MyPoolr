#!/usr/bin/env python3
"""CLI tool for managing localization."""

import asyncio
import argparse
import json
import sys
import csv
from pathlib import Path
from typing import Dict, Any, List

from database import db_manager
from services.localization_service import LocalizationService
from models.localization import MessageCategory, LocalizationContext


async def list_locales(args):
    """List supported locales."""
    service = LocalizationService(db_manager.service_client)
    
    locales = await service.get_supported_locales(active_only=not args.all)
    
    if locales:
        print("Supported locales:")
        print(f"{'Code':<10} {'Language':<20} {'Native Name':<25} {'Active':<8} {'Progress':<10}")
        print("-" * 80)
        
        for locale in locales:
            active = "Yes" if locale.is_active else "No"
            progress = f"{locale.completion_percentage}%"
            print(f"{locale.locale_code:<10} {locale.language_name:<20} {locale.native_name:<25} {active:<8} {progress:<10}")
    else:
        print("No locales found")


async def add_template(args):
    """Add a message template."""
    service = LocalizationService(db_manager.service_client)
    
    category = MessageCategory(args.category)
    placeholders = args.placeholders.split(',') if args.placeholders else []
    
    success = await service.add_message_template(
        key=args.key,
        default_text=args.text,
        category=category,
        description=args.description,
        placeholders=placeholders
    )
    
    if success:
        print(f"Successfully added template: {args.key}")
    else:
        print(f"Failed to add template: {args.key}")
        sys.exit(1)


async def add_translation(args):
    """Add a translation."""
    service = LocalizationService(db_manager.service_client)
    
    success = await service.add_localized_message(
        template_key=args.key,
        locale_code=args.locale,
        translated_text=args.text,
        translator_notes=args.notes
    )
    
    if success:
        print(f"Successfully added translation: {args.key} -> {args.locale}")
    else:
        print(f"Failed to add translation: {args.key} -> {args.locale}")
        sys.exit(1)


async def get_message(args):
    """Get a localized message."""
    service = LocalizationService(db_manager.service_client)
    
    context = LocalizationContext(locale_code=args.locale)
    
    placeholders = {}
    if args.placeholders:
        try:
            placeholders = json.loads(args.placeholders)
        except json.JSONDecodeError:
            print("Invalid JSON for placeholders")
            sys.exit(1)
    
    message = await service.get_message(args.key, context, placeholders)
    
    print(f"Key: {args.key}")
    print(f"Locale: {args.locale}")
    print(f"Message: {message}")


async def export_translations(args):
    """Export translations to CSV."""
    service = LocalizationService(db_manager.service_client)
    
    # Get all templates
    result = db_manager.service_client.table("message_template").select("*").eq("is_active", True).execute()
    
    if not result.data:
        print("No templates found")
        return
    
    templates = result.data
    
    # Get translations for locale
    translations = {}
    if args.locale != "templates":
        locale_result = db_manager.service_client.table("localized_message").select("template_id, translated_text").eq("locale_code", args.locale).eq("status", "active").execute()
        
        if locale_result.data:
            for trans in locale_result.data:
                translations[trans["template_id"]] = trans["translated_text"]
    
    # Write CSV
    output_file = Path(args.output) if args.output else Path(f"translations_{args.locale}.csv")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['key', 'category', 'default_text', 'translated_text', 'description', 'placeholders']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        
        for template in templates:
            translated_text = translations.get(template["id"], "")
            
            writer.writerow({
                'key': template["key"],
                'category': template["category"],
                'default_text': template["default_text"],
                'translated_text': translated_text,
                'description': template.get("description", ""),
                'placeholders': ','.join(template.get("placeholders", []))
            })
    
    print(f"Exported translations to {output_file}")


async def import_translations(args):
    """Import translations from CSV."""
    service = LocalizationService(db_manager.service_client)
    
    input_file = Path(args.input)
    if not input_file.exists():
        print(f"File not found: {input_file}")
        sys.exit(1)
    
    success_count = 0
    error_count = 0
    
    with open(input_file, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            key = row['key']
            translated_text = row['translated_text']
            
            if not translated_text.strip():
                continue  # Skip empty translations
            
            success = await service.add_localized_message(
                template_key=key,
                locale_code=args.locale,
                translated_text=translated_text,
                translator_notes=row.get('notes', '')
            )
            
            if success:
                success_count += 1
                print(f"✓ {key}")
            else:
                error_count += 1
                print(f"✗ {key}")
    
    print(f"\nImport completed: {success_count} success, {error_count} errors")


async def show_progress(args):
    """Show translation progress."""
    service = LocalizationService(db_manager.service_client)
    
    if args.locale:
        # Show progress for specific locale
        progress = await service.get_translation_progress(args.locale)
        
        print(f"Translation progress for {args.locale}:")
        print(f"  Total templates: {progress['total_templates']}")
        print(f"  Translated: {progress['translated_count']}")
        print(f"  Missing: {progress['missing_count']}")
        print(f"  Completion: {progress['completion_percentage']:.1f}%")
    else:
        # Show progress for all locales
        locales = await service.get_supported_locales(active_only=True)
        
        print("Translation progress for all locales:")
        print(f"{'Locale':<10} {'Language':<20} {'Progress':<10} {'Translated':<12} {'Missing':<8}")
        print("-" * 70)
        
        for locale in locales:
            progress = await service.get_translation_progress(locale.locale_code)
            
            print(f"{locale.locale_code:<10} {locale.language_name:<20} {progress['completion_percentage']:>6.1f}% {progress['translated_count']:>8}/{progress['total_templates']:<3} {progress['missing_count']:>6}")


async def validate_translations(args):
    """Validate translations for issues."""
    service = LocalizationService(db_manager.service_client)
    
    print(f"Validating translations for {args.locale}...")
    
    # Get all templates with placeholders
    result = db_manager.service_client.table("message_template").select("*").eq("is_active", True).execute()
    
    if not result.data:
        print("No templates found")
        return
    
    issues = []
    
    for template in result.data:
        key = template["key"]
        placeholders = template.get("placeholders", [])
        
        # Get translation
        context = LocalizationContext(locale_code=args.locale)
        message = await service.get_message(key, context)
        
        # Check for missing placeholders
        for placeholder in placeholders:
            placeholder_pattern = f"{{{placeholder}}}"
            if placeholder_pattern not in message:
                issues.append(f"{key}: Missing placeholder '{placeholder}'")
        
        # Check for extra placeholders (simplified check)
        import re
        found_placeholders = re.findall(r'\{(\w+)\}', message)
        for found in found_placeholders:
            if found not in placeholders:
                issues.append(f"{key}: Unexpected placeholder '{found}'")
    
    if issues:
        print(f"Found {len(issues)} issues:")
        for issue in issues:
            print(f"  ⚠️  {issue}")
    else:
        print("✅ No issues found")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Localization Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List locales command
    list_parser = subparsers.add_parser("locales", help="List supported locales")
    list_parser.add_argument("--all", action="store_true", help="Include inactive locales")
    
    # Add template command
    template_parser = subparsers.add_parser("add-template", help="Add message template")
    template_parser.add_argument("key", help="Template key")
    template_parser.add_argument("text", help="Default text")
    template_parser.add_argument("category", choices=["ui", "notification", "error", "validation", "help"], help="Template category")
    template_parser.add_argument("--description", help="Template description")
    template_parser.add_argument("--placeholders", help="Comma-separated placeholder names")
    
    # Add translation command
    trans_parser = subparsers.add_parser("add-translation", help="Add translation")
    trans_parser.add_argument("key", help="Template key")
    trans_parser.add_argument("locale", help="Locale code")
    trans_parser.add_argument("text", help="Translated text")
    trans_parser.add_argument("--notes", help="Translator notes")
    
    # Get message command
    get_parser = subparsers.add_parser("get", help="Get localized message")
    get_parser.add_argument("key", help="Message key")
    get_parser.add_argument("locale", help="Locale code")
    get_parser.add_argument("--placeholders", help="JSON placeholders")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export translations to CSV")
    export_parser.add_argument("locale", help="Locale code or 'templates' for template export")
    export_parser.add_argument("--output", help="Output file path")
    
    # Import command
    import_parser = subparsers.add_parser("import", help="Import translations from CSV")
    import_parser.add_argument("locale", help="Locale code")
    import_parser.add_argument("input", help="Input CSV file path")
    
    # Progress command
    progress_parser = subparsers.add_parser("progress", help="Show translation progress")
    progress_parser.add_argument("--locale", help="Specific locale code")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate translations")
    validate_parser.add_argument("locale", help="Locale code to validate")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Run the appropriate command
    if args.command == "locales":
        asyncio.run(list_locales(args))
    elif args.command == "add-template":
        asyncio.run(add_template(args))
    elif args.command == "add-translation":
        asyncio.run(add_translation(args))
    elif args.command == "get":
        asyncio.run(get_message(args))
    elif args.command == "export":
        asyncio.run(export_translations(args))
    elif args.command == "import":
        asyncio.run(import_translations(args))
    elif args.command == "progress":
        asyncio.run(show_progress(args))
    elif args.command == "validate":
        asyncio.run(validate_translations(args))


if __name__ == "__main__":
    main()