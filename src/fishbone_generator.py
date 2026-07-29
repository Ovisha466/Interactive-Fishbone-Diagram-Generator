# Importing libraries
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Wedge
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from textwrap import wrap
import numpy as np

# Utilities

def normalize_col_name(name: str) -> str:
    return ''.join(ch for ch in name.lower() if ch.isalnum())

def find_best_column(df: pd.DataFrame, candidates):
    df_norm_map = {normalize_col_name(col): col for col in df.columns}
    for cand in candidates:
        norm = normalize_col_name(cand)
        if norm in df_norm_map:
            return df_norm_map[norm]
    return None

# Loading Excel

def load_data_from_excel(file_path, sheet_name=0, skiprows=None, print_diagnostics=True):
    df = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=skiprows, engine=None)

    expected = {
        'problem_code': ['PROBLEM_CODE', 'Problem Code', 'problemcode', 'problem_code'],
        'failure_code': ['FAILURE_CODE', 'Failure Code', 'failurecode', 'failure_code'],
        'failure_mode': ['FAILURE_MODE', 'Failure Mode', 'failuremode', 'failure_mode'],
        'product_id': ['Product ID', 'PRODUCT_ID', 'productid', 'product_id'],
        'key_driver': ['Key driver', 'KeyDriver', 'Key Driver', 'KEY_DRIVER', 'keydriver'],
        'cpn': ['CPN', 'Cpn', 'cpn']
    }

    resolved = {}
    for key, candidates in expected.items():
        col = find_best_column(df, candidates)
        resolved[key] = col

    if print_diagnostics:
        found = {k: v for k, v in resolved.items() if v is not None}
        missing = [k for k, v in resolved.items() if v is None]
        print("Column resolution:")
        for k, v in found.items():
            print(f"  {k:12s} -> '{v}'")
        if missing:
            print(f"Missing logical columns (will be handled gracefully): {missing}")

    return df, resolved

# Plotting utilities

def init_enhanced_plot():
    fig, ax = plt.subplots(figsize=(40, 32))  # Further increased figure size
    ax.set_xlim(-18, 18)  # More horizontal space
    ax.set_ylim(-16, 16)  # More vertical space
    ax.axis('off')
    return fig, ax

def draw_enhanced_spine(ax, head_label):
    spine_left = -15.5  # Extended spine
    spine_right = 15.5   # Extended spine
    ax.plot([spine_left, spine_right], [0, 0], color='#2E86AB', linewidth=4, alpha=0.9)

    head_radius = 0.6
    head = Wedge((spine_right, 0), head_radius, 270, 90, fc='#A23B72', ec='#A23B72', alpha=0.95)
    ax.add_patch(head)

    wrapped_head_label = "\n".join(wrap(str(head_label), width=30))
    ax.text(spine_right + head_radius + 0.2, 0, wrapped_head_label, fontsize=12,
            fontweight='bold', color='white', va='center', ha='left',
            bbox=dict(facecolor='#A23B72', edgecolor='none', pad=5, alpha=0.95))

    tail_width = 0.8
    tail_height = 1.2
    tail_pts = np.array([
        [spine_left - tail_width, -tail_height / 2],
        [spine_left - tail_width, tail_height / 2],
        [spine_left, 0]
    ])
    ax.add_patch(Polygon(tail_pts, closed=True, fc='#2E86AB', ec='#2E86AB', alpha=0.9))

def calculate_bone_requirements(primary_bones):
    """Calculate space requirements for each bone"""
    bone_requirements = {}
    
    for bone_label, count, secondary_groups in primary_bones:
        total_items = 0
        max_depth = 0
        max_tertiary_per_secondary = 0
        
        def calculate_group_depth(groups, current_depth=1):
            nonlocal max_depth, max_tertiary_per_secondary
            max_depth = max(max_depth, current_depth)
            for group in groups:
                if len(group) == 3:  # (column, items, nested_groups)
                    _, items, nested_groups = group
                    for item in items:
                        if len(item) == 3:  # Item with tertiary groups
                            _, _, item_tertiary = item
                            if item_tertiary:
                                current_tertiary_count = sum(len(ter_items) for _, ter_items, _ in item_tertiary)
                                max_tertiary_per_secondary = max(max_tertiary_per_secondary, current_tertiary_count)
                                calculate_group_depth(item_tertiary, current_depth + 1)
                    if nested_groups:
                        calculate_group_depth(nested_groups, current_depth + 1)
        
        def calculate_total_items(groups):
            nonlocal total_items
            for group in groups:
                if len(group) == 3:
                    _, items, nested_groups = group
                    total_items += len(items)
                    for item in items:
                        if len(item) == 3:  # Item with tertiary groups
                            _, _, item_tertiary = item
                            if item_tertiary:
                                calculate_total_items(item_tertiary)
                    if nested_groups:
                        calculate_total_items(nested_groups)
        
        calculate_group_depth(secondary_groups)
        calculate_total_items(secondary_groups)
        
        # Space calculation
        vertical_requirement = 3.0 + (total_items * 0.4) + (max_depth * 2.0) + (max_tertiary_per_secondary * 0.3)
        horizontal_requirement = 2.0 + (max_depth * 2.5) + (max_tertiary_per_secondary * 0.4)
        
        bone_requirements[bone_label] = {
            'vertical': min(vertical_requirement, 10.0),
            'horizontal': min(horizontal_requirement, 8.0),
            'total_items': total_items,
            'max_depth': max_depth,
            'max_tertiary_per_secondary': max_tertiary_per_secondary
        }
    
    return bone_requirements

def calculate_non_overlapping_positions(primary_bones):
    """Calculate positions for primary bones to prevent overlapping"""
    positions = {}
    bone_requirements = calculate_bone_requirements(primary_bones)
    
    top_bones = []
    bottom_bones = []
    
    # Sort bones by complexity
    sorted_bones = sorted(primary_bones, 
                         key=lambda x: bone_requirements[x[0]]['total_items'] + 
                                     (bone_requirements[x[0]]['max_depth'] * 2) +
                                     (bone_requirements[x[0]]['max_tertiary_per_secondary'] * 3), 
                         reverse=True)
    
    total_top_requirement = 0
    total_bottom_requirement = 0
    
    for bone in sorted_bones:
        bone_label = bone[0]
        requirement = bone_requirements[bone_label]['vertical']
        
        if total_top_requirement <= total_bottom_requirement:
            top_bones.append(bone)
            total_top_requirement += requirement
        else:
            bottom_bones.append(bone)
            total_bottom_requirement += requirement
    
    max_bones_per_side = max(len(top_bones), len(bottom_bones))
    x_span = min(26.0, 10.0 + max_bones_per_side * 2.2)
    x_left = -(x_span / 2)
    x_right = (x_span / 2)
    
    # Position top bones
    if top_bones:
        total_top_space = sum(bone_requirements[b[0]]['horizontal'] for b in top_bones)
        available_space = x_right - x_left - 3.0
        spacing_ratio = available_space / total_top_space if total_top_space > 0 else 1.0
        
        current_x = x_left + 1.5
        for bone in top_bones:
            bone_label = bone[0]
            bone_width = bone_requirements[bone_label]['horizontal'] * spacing_ratio * 1.2
            positions[bone_label] = {
                'x': current_x + bone_width / 2,
                'y': 0.0,
                'branch_direction': 'top',
                'subcategories': bone[2],
                'bone_width': bone_width
            }
            current_x += bone_width + 0.3
    
    # Position bottom bones
    if bottom_bones:
        total_bottom_space = sum(bone_requirements[b[0]]['horizontal'] for b in bottom_bones)
        available_space = x_right - x_left - 3.0
        spacing_ratio = available_space / total_bottom_space if total_bottom_space > 0 else 1.0
        
        current_x = x_left + 1.5
        for bone in bottom_bones:
            bone_label = bone[0]
            bone_width = bone_requirements[bone_label]['horizontal'] * spacing_ratio * 1.2
            positions[bone_label] = {
                'x': current_x + bone_width / 2,
                'y': 0.0,
                'branch_direction': 'bottom',
                'subcategories': bone[2],
                'bone_width': bone_width
            }
            current_x += bone_width + 0.3
    
    return positions

def wrap_text(text, max_width=18):
    """Improved text wrapping"""
    text_str = str(text)
    if any(char.isdigit() for char in text_str) and len(text_str) <= 15:
        max_width = 22
    return "\n".join(wrap(text_str, width=max_width, break_long_words=True, break_on_hyphens=False))
def calculate_bone_requirements(primary_bones):
    """Calculate space requirements for each bone"""
    bone_requirements = {}
    
    for bone_label, count, secondary_groups in primary_bones:
        total_items = 0
        max_depth = 0
        max_tertiary_per_secondary = 0
        
        def calculate_group_depth(groups, current_depth=1):
            nonlocal max_depth, max_tertiary_per_secondary
            max_depth = max(max_depth, current_depth)
            for group in groups:
                if len(group) == 3:  # (column, items, nested_groups)
                    _, items, nested_groups = group
                    for item in items:
                        if len(item) == 3:  # Item with tertiary groups
                            _, _, item_tertiary = item
                            if item_tertiary:
                                current_tertiary_count = sum(len(ter_items) for _, ter_items, _ in item_tertiary)
                                max_tertiary_per_secondary = max(max_tertiary_per_secondary, current_tertiary_count)
                                calculate_group_depth(item_tertiary, current_depth + 1)
                    if nested_groups:
                        calculate_group_depth(nested_groups, current_depth + 1)
        
        def calculate_total_items(groups):
            nonlocal total_items
            for group in groups:
                if len(group) == 3:
                    _, items, nested_groups = group
                    total_items += len(items)
                    for item in items:
                        if len(item) == 3:  # Item with tertiary groups
                            _, _, item_tertiary = item
                            if item_tertiary:
                                calculate_total_items(item_tertiary)
                    if nested_groups:
                        calculate_total_items(nested_groups)
        
        calculate_group_depth(secondary_groups)
        calculate_total_items(secondary_groups)
        
        # Space calculation
        vertical_requirement = 3.0 + (total_items * 0.4) + (max_depth * 2.0) + (max_tertiary_per_secondary * 0.3)
        horizontal_requirement = 2.0 + (max_depth * 2.5) + (max_tertiary_per_secondary * 0.4)
        
        bone_requirements[bone_label] = {
            'vertical': min(vertical_requirement, 10.0),
            'horizontal': min(horizontal_requirement, 8.0),
            'total_items': total_items,
            'max_depth': max_depth,
            'max_tertiary_per_secondary': max_tertiary_per_secondary
        }
    
    return bone_requirements

def calculate_non_overlapping_positions(primary_bones):
    """Calculate positions for primary bones to prevent overlapping"""
    positions = {}
    bone_requirements = calculate_bone_requirements(primary_bones)
    
    top_bones = []
    bottom_bones = []
    
    # Sort bones by complexity
    sorted_bones = sorted(primary_bones, 
                         key=lambda x: bone_requirements[x[0]]['total_items'] + 
                                     (bone_requirements[x[0]]['max_depth'] * 2) +
                                     (bone_requirements[x[0]]['max_tertiary_per_secondary'] * 3), 
                         reverse=True)
    
    total_top_requirement = 0
    total_bottom_requirement = 0
    
    for bone in sorted_bones:
        bone_label = bone[0]
        requirement = bone_requirements[bone_label]['vertical']
        
        if total_top_requirement <= total_bottom_requirement:
            top_bones.append(bone)
            total_top_requirement += requirement
        else:
            bottom_bones.append(bone)
            total_bottom_requirement += requirement
    
    max_bones_per_side = max(len(top_bones), len(bottom_bones))
    x_span = min(26.0, 10.0 + max_bones_per_side * 2.2)
    x_left = -(x_span / 2)
    x_right = (x_span / 2)
    
    # Position top bones
    if top_bones:
        total_top_space = sum(bone_requirements[b[0]]['horizontal'] for b in top_bones)
        available_space = x_right - x_left - 3.0
        spacing_ratio = available_space / total_top_space if total_top_space > 0 else 1.0
        
        current_x = x_left + 1.5
        for bone in top_bones:
            bone_label = bone[0]
            bone_width = bone_requirements[bone_label]['horizontal'] * spacing_ratio * 1.2
            positions[bone_label] = {
                'x': current_x + bone_width / 2,
                'y': 0.0,
                'branch_direction': 'top',
                'subcategories': bone[2],
                'bone_width': bone_width
            }
            current_x += bone_width + 0.3
    
    # Position bottom bones
    if bottom_bones:
        total_bottom_space = sum(bone_requirements[b[0]]['horizontal'] for b in bottom_bones)
        available_space = x_right - x_left - 3.0
        spacing_ratio = available_space / total_bottom_space if total_bottom_space > 0 else 1.0
        
        current_x = x_left + 1.5
        for bone in bottom_bones:
            bone_label = bone[0]
            bone_width = bone_requirements[bone_label]['horizontal'] * spacing_ratio * 1.2
            positions[bone_label] = {
                'x': current_x + bone_width / 2,
                'y': 0.0,
                'branch_direction': 'bottom',
                'subcategories': bone[2],
                'bone_width': bone_width
            }
            current_x += bone_width + 0.3
    
    return positions
def calculate_vertical_distribution(items, available_height, direction, level=0, item_tertiary_counts=None):
    """Calculate optimal vertical positions with dynamic spacing based on tertiary content"""
    if not items:
        return []
    
    n_items = len(items)
    
    if n_items == 1:
        return [available_height * 0.5]
    
    # Calculate spacing based on tertiary content if provided
    if item_tertiary_counts and len(item_tertiary_counts) == n_items:
        # Items with more tertiary content get more space
        total_tertiary = sum(item_tertiary_counts)
        if total_tertiary > 0:
            # Dynamic spacing: items with more tertiary content get more vertical space
            base_spacings = []
            for tertiary_count in item_tertiary_counts:
                # Base spacing + extra for tertiary content
                spacing_factor = 1.0 + (tertiary_count * 0.3)
                base_spacings.append(spacing_factor)
            
            # Normalize to fit available height
            total_base = sum(base_spacings)
            normalized_spacings = [s / total_base * available_height * 0.8 for s in base_spacings]
            
            positions = []
            current_pos = available_height * 0.1  # Start with some margin
            for spacing in normalized_spacings:
                positions.append(current_pos + spacing / 2)
                current_pos += spacing
            return positions
    
    # Fallback: equal spacing for items without tertiary content info
    if level == 0:  # Secondary level
        spacing = available_height / (n_items + 2)
    else:  # Tertiary level
        spacing = available_height / (n_items + 3)
    
    if direction == 'top':
        start_y = available_height * 0.15
        positions = [start_y + i * spacing for i in range(n_items)]
    else:
        start_y = available_height * 0.85
        positions = [start_y - i * spacing for i in range(n_items)]
    
    return positions

def plot_nested_categories(ax, start_x, start_y, direction, category_color, groups, level=0):
    """Recursively plot nested categories with uneven bone lengths and better space utilization"""
    if not groups:
        return
        
    # Calculate item-specific offsets based on tertiary content
    for grp_idx, group_data in enumerate(groups):
        if len(group_data) == 3:
            sec_column, items, nested_groups = group_data
        else:
            items = group_data
            sec_column = f"Level_{level}"
            nested_groups = []
        
        # Calculate tertiary counts for each item to determine spacing
        item_tertiary_counts = []
        for item_data in items:
            tertiary_count = 0
            if len(item_data) == 3:
                _, _, tertiary_groups = item_data
                if tertiary_groups:
                    tertiary_count = sum(len(ter_items) for _, ter_items, _ in tertiary_groups)
            item_tertiary_counts.append(tertiary_count)
        
        # Calculate available height - use more space for levels with tertiary content
        if direction == 'top':
            available_height = 14.0 - (level * 0.5)  # More height available
        else:
            available_height = 14.0 - (level * 0.5)  # More height available
        
        # Get positions with tertiary-aware spacing
        sub_y_positions = calculate_vertical_distribution(
            items, available_height, direction, level, item_tertiary_counts
        )
        
        for idx, item_data in enumerate(items):
            if idx >= len(sub_y_positions):
                continue
                
            # Handle item data
            if len(item_data) == 2:
                subcat, sub_count = item_data
                tertiary_groups = []
            elif len(item_data) == 3:
                subcat, sub_count, tertiary_groups = item_data
            else:
                subcat = str(item_data[0]) if len(item_data) > 0 else "Unknown"
                sub_count = item_data[1] if len(item_data) > 1 else 0
                tertiary_groups = []
                
            sub_y = sub_y_positions[idx] if direction == 'top' else -sub_y_positions[idx]
            
            # CRITICAL IMPROVEMENT: Dynamic offset based on tertiary content
            tertiary_item_count = 0
            if tertiary_groups:
                tertiary_item_count = sum(len(ter_items) for _, ter_items, _ in tertiary_groups)
            
            # Base offset + dynamic adjustment for tertiary content
            base_offset = 2.5 + (level * 1.8)
            # Items with more tertiary content get longer bones to utilize space
            tertiary_offset = tertiary_item_count * 0.4
            dynamic_offset = base_offset + tertiary_offset
            
            # Ensure minimum offset for visibility
            connector_x = start_x - max(dynamic_offset, 2.0)
            
            # IMPROVED CONNECTOR: Draw line that definitely reaches the tertiary value
            line_style = '--' if level > 0 else '-'
            line_width = 2.2 - (level * 0.2)
            
            # Draw the connector line - ensure it goes exactly to the marker
            ax.plot([start_x, connector_x], [start_y, sub_y],
                    color=category_color, linewidth=max(line_width, 1.2), 
                    alpha=0.9, linestyle=line_style)
            
            # Draw marker at exact endpoint - make it more visible
            marker_size = 8 - (level * 0.5)
            ax.plot(connector_x, sub_y, 'o', color=category_color, 
                   markersize=max(marker_size, 5), alpha=0.95, 
                   markeredgecolor='white', markeredgewidth=1.5)
            
            # Draw text with improved positioning
            font_size = 10 - (level * 0.5)
            sub_label_text = f"{wrap_text(subcat, 14)}\n({sub_count})"
            
            # Smart text positioning based on available space
            text_x_offset = 0.3 + (level * 0.2)
            text_x = connector_x - text_x_offset
            
            # Adjust vertical alignment based on position to avoid collisions
            if direction == 'top':
                if idx == 0:  # Top item
                    va = 'bottom'
                elif idx == len(items) - 1:  # Bottom item  
                    va = 'top'
                else:
                    va = 'center'
            else:
                if idx == 0:  # Top item (in bottom direction)
                    va = 'top'
                elif idx == len(items) - 1:  # Bottom item
                    va = 'bottom'
                else:
                    va = 'center'
            
            ax.text(text_x, sub_y, sub_label_text, fontsize=max(font_size, 8), fontweight='bold',
                    color='#1f2d3d', va=va, ha='right',
                    bbox=dict(facecolor='white', edgecolor=category_color,
                              boxstyle='round,pad=0.3', alpha=0.95, linewidth=0.8))
            
            # Recursively plot tertiary groups with SPREAD OUT layout
            if tertiary_groups:
                # Calculate how much horizontal space we can use
                max_tertiary_items = max(len(ter_items) for _, ter_items, _ in tertiary_groups) if tertiary_groups else 0
                
                # Use more horizontal space for tertiary items to spread them out
                tertiary_base_offset = 2.0 + (max_tertiary_items * 0.25)
                
                # Plot tertiary groups with the new dynamic offset
                plot_nested_categories(ax, connector_x, sub_y, direction, category_color, 
                                     tertiary_groups, level + 1)
            
            # Plot nested groups
            if nested_groups:
                plot_nested_categories(ax, connector_x, sub_y, direction, category_color, 
                                     nested_groups, level + 1)

def plot_enhanced_category(ax, bone_label, count, positions, color, secondary_groups=None):
    if bone_label not in positions:
        return
        
    pos_data = positions[bone_label]
    x_pos = pos_data['x']
    direction = pos_data['branch_direction']

    def calculate_branch_length(groups, depth=0):
        if not groups:
            return 3.5  # Base length
            
        max_length = 3.5
        for group in groups:
            if len(group) == 3:
                _, items, nested_groups = group
                # Calculate length based on actual content
                group_tertiary_content = 0
                for item in items:
                    if len(item) == 3:
                        _, _, tertiary_groups = item
                        if tertiary_groups:
                            group_tertiary_content += sum(len(ter_items) for _, ter_items, _ in tertiary_groups)
                
                # Dynamic length: more tertiary content = longer bones
                group_length = 2.5 + (len(items) * 0.2) + (group_tertiary_content * 0.15) + (depth * 1.2)
                max_length = max(max_length, group_length)
                
                # Recursively calculate for nested content
                for item in items:
                    if len(item) == 3:
                        _, _, tertiary_groups = item
                        if tertiary_groups:
                            tertiary_length = calculate_branch_length(tertiary_groups, depth + 1)
                            max_length = max(max_length, group_length + tertiary_length * 0.5)
                
                if nested_groups:
                    nested_length = calculate_branch_length(nested_groups, depth + 1)
                    max_length = max(max_length, group_length + nested_length * 0.5)
        
        return min(max_length, 12.0)  # Increased maximum length

    branch_length = calculate_branch_length(secondary_groups) if secondary_groups else 3.0

    if direction == 'top':
        branch_end_y = branch_length
        text_va = 'bottom'
        sub_offset = 0.6
    else:
        branch_end_y = -branch_length
        text_va = 'top'
        sub_offset = -0.6

    if color is None:
        color_map = [
            (0.2, 0.4, 0.6, 1.0), (0.6, 0.2, 0.4, 1.0), (0.3, 0.6, 0.3, 1.0),
            (0.7, 0.4, 0.1, 1.0), (0.4, 0.3, 0.6, 1.0), (0.6, 0.3, 0.2, 1.0),
            (0.2, 0.5, 0.5, 1.0), (0.5, 0.2, 0.5, 1.0), (0.3, 0.3, 0.7, 1.0),
            (0.7, 0.2, 0.3, 1.0), (0.4, 0.5, 0.2, 1.0), (0.5, 0.3, 0.4, 1.0)
        ]
        category_idx = hash(bone_label) % len(color_map)
        category_color = color_map[category_idx]
    else:
        category_color = color

    # Draw main bone line
    line_width = 3.5 if secondary_groups else 2.5
    ax.plot([x_pos, x_pos], [0.0, branch_end_y], color=category_color, 
            linewidth=line_width, alpha=0.95)

    # Draw bone label
    label_text = f"{wrap_text(bone_label, 16)}\n({count})"
    ax.text(x_pos, branch_end_y + sub_offset, label_text, fontsize=11, fontweight='bold',
            color=category_color, ha='center', va=text_va,
            bbox=dict(facecolor='white', edgecolor=category_color,
                      boxstyle='round,pad=0.5', alpha=0.95, linewidth=1.5))

    # Plot nested categories with improved space utilization
    if secondary_groups and len(secondary_groups) > 0:
        plot_nested_categories(ax, x_pos, branch_end_y, direction, category_color, secondary_groups)

# Creating fishbone from excel - PROPERLY FIXED COUNT SYNCHRONIZATION

def create_enhanced_fishbone_from_excel(file_path, bone_configs, head_label="All Data", sheet_name=0):
    df, cols = load_data_from_excel(file_path, sheet_name=sheet_name, print_diagnostics=True)

    filtered_df = df.copy()

    # Separate configuration types
    primary_configs = [config for config in bone_configs if config.get('type', 'primary') == 'primary']
    secondary_configs = [config for config in bone_configs if config.get('type', 'primary') == 'secondary']
    tertiary_configs = [config for config in bone_configs if config.get('type', 'primary') == 'tertiary']
    filter_configs = [config for config in bone_configs if config.get('type', 'primary') == 'filter']

    # Apply filter configs first
    for config in filter_configs:
        column = config.get('column')
        selected_values = config.get('values', []) or []
        if column and selected_values and column in filtered_df.columns:
            if any(pd.isna(v) for v in selected_values):
                non_nans = [v for v in selected_values if not pd.isna(v)]
                mask = filtered_df[column].isin(non_nans) | filtered_df[column].isna()
                filtered_df = filtered_df[mask]
            else:
                filtered_df = filtered_df[filtered_df[column].isin(selected_values)]

    # FIXED: Calculate total issues by applying ALL selections step by step
    # Start with the base filtered data after problem and filter configs
    total_df = filtered_df.copy()
    
    # Apply primary bone selections
    for config in primary_configs:
        column = config.get('column')
        selected_values = config.get('values', []) or []
        if column and selected_values and column in total_df.columns:
            if any(pd.isna(v) for v in selected_values):
                non_nans = [v for v in selected_values if not pd.isna(v)]
                mask = total_df[column].isin(non_nans) | total_df[column].isna()
                total_df = total_df[mask]
            else:
                total_df = total_df[total_df[column].isin(selected_values)]
    
    # Apply secondary bone selections
    for config in secondary_configs:
        column = config.get('column')
        selected_values = config.get('values', []) or []
        if column and selected_values and column in total_df.columns:
            if any(pd.isna(v) for v in selected_values):
                non_nans = [v for v in selected_values if not pd.isna(v)]
                mask = total_df[column].isin(non_nans) | total_df[column].isna()
                total_df = total_df[mask]
            else:
                total_df = total_df[total_df[column].isin(selected_values)]
    
    # Apply tertiary bone selections
    for config in tertiary_configs:
        column = config.get('column')
        selected_values = config.get('values', []) or []
        if column and selected_values and column in total_df.columns:
            if any(pd.isna(v) for v in selected_values):
                non_nans = [v for v in selected_values if not pd.isna(v)]
                mask = total_df[column].isin(non_nans) | total_df[column].isna()
                total_df = total_df[mask]
            else:
                total_df = total_df[total_df[column].isin(selected_values)]

    # CRITICAL FIX: The actual total issues is the count after ALL selections
    actual_total_issues = len(total_df)

    # Now build the primary bones structure for visualization (using the original logic)
    primary_bones = []
    
    for config in primary_configs:
        column = config.get('column')
        selected_values = config.get('values', []) or []
        top_k = config.get('top_k', 0)

        if column not in df.columns:
            print(f"Warning: Column '{column}' not found in data. Skipping.")
            continue

        working_series = filtered_df[column]

        if selected_values:
            if any(pd.isna(v) for v in selected_values):
                non_nans = [v for v in selected_values if not pd.isna(v)]
                mask = working_series.isin(non_nans) | working_series.isna()
                working_series = working_series[mask]
            else:
                working_series = working_series[working_series.isin(selected_values)]

        if top_k > 0:
            value_counts = working_series.value_counts(dropna=False).head(top_k)
        else:
            value_counts = working_series.value_counts(dropna=False)

        for label, count in value_counts.items():
            if pd.isna(label):
                label_str = "<NaN>"
            else:
                label_str = str(label)
            
            # Get data for this primary bone value
            bone_data = filtered_df[filtered_df[column] == label] if column in filtered_df.columns else filtered_df
            
            # Build secondary groups
            secondary_groups = []
            for sec_config in secondary_configs:
                sec_column = sec_config.get('column')
                sec_selected_values = sec_config.get('values', []) or []
                
                if sec_column and sec_column in bone_data.columns:
                    # FIXED: Apply secondary filtering to get actual counts
                    sec_working_data = bone_data[sec_column]
                    
                    if sec_selected_values:
                        if any(pd.isna(v) for v in sec_selected_values):
                            non_nans = [v for v in sec_selected_values if not pd.isna(v)]
                            sec_mask = sec_working_data.isin(non_nans) | sec_working_data.isna()
                            sec_working_data = sec_working_data[sec_mask]
                        else:
                            sec_working_data = sec_working_data[sec_working_data.isin(sec_selected_values)]
                    
                    sec_counts = sec_working_data.value_counts(dropna=False).head(10)
                    sec_items = []
                    
                    for sec_label, sec_count in sec_counts.items():
                        if sec_selected_values and sec_label not in sec_selected_values:
                            continue
                            
                        if pd.isna(sec_label):
                            sec_label_str = "<NaN>"
                        else:
                            sec_label_str = str(sec_label)
                        
                        # Build tertiary groups for this secondary value
                        tertiary_groups = []
                        for ter_config in tertiary_configs:
                            ter_column = ter_config.get('column')
                            ter_selected_values = ter_config.get('values', []) or []
                            
                            if ter_column and ter_column in bone_data.columns:
                                # Filter data for this specific secondary value
                                if pd.isna(sec_label) or sec_label_str == "<NaN>":
                                    ter_data = bone_data[bone_data[sec_column].isna()]
                                else:
                                    ter_data = bone_data[bone_data[sec_column] == sec_label]
                                
                                # FIXED: Apply tertiary filtering to get actual counts
                                ter_working_data = ter_data[ter_column]
                                
                                if ter_selected_values:
                                    if any(pd.isna(v) for v in ter_selected_values):
                                        non_nans = [v for v in ter_selected_values if not pd.isna(v)]
                                        ter_mask = ter_working_data.isin(non_nans) | ter_working_data.isna()
                                        ter_working_data = ter_working_data[ter_mask]
                                    else:
                                        ter_working_data = ter_working_data[ter_working_data.isin(ter_selected_values)]
                                
                                ter_counts = ter_working_data.value_counts(dropna=False).head(5)
                                ter_items = []
                                
                                for ter_label, ter_count in ter_counts.items():
                                    if ter_selected_values and ter_label not in ter_selected_values:
                                        continue
                                        
                                    if pd.isna(ter_label):
                                        ter_label_str = "<NaN>"
                                    else:
                                        ter_label_str = str(ter_label)
                                    ter_items.append((ter_label_str, ter_count))
                                
                                if ter_items:
                                    tertiary_groups.append((ter_column, ter_items, []))
                        
                        # FIXED: Use actual filtered count for secondary items
                        actual_sec_count = sec_count  # This now reflects the filtered count
                        sec_items.append((sec_label_str, int(actual_sec_count), tertiary_groups))
                    
                    if sec_items:
                        secondary_groups.append((sec_column, sec_items, []))
            
            # FIXED: Use actual filtered count for primary items
            actual_primary_count = count  # This now reflects the filtered count
            primary_bones.append((label_str, int(actual_primary_count), secondary_groups))

    if not primary_bones:
        messagebox.showwarning("No Data", "No data available after filtering.")
        return

    print("Primary bones to plot:")
    for bone, count, secondary_groups in primary_bones:
        print(f"  {bone}: {count}")
        if secondary_groups:
            for sec_col, items, _ in secondary_groups:
                print(f"    {sec_col}:")
                for item_label, item_count, tertiary_groups in items:
                    print(f"      - {item_label}: {item_count}")
                    if tertiary_groups:
                        for ter_col, ter_items, _ in tertiary_groups:
                            print(f"        -> {ter_col}: {ter_items}")

    fig, ax = init_enhanced_plot()
    
    positions = calculate_non_overlapping_positions(primary_bones)
    draw_enhanced_spine(ax, head_label)

    color_map = [
        (0.2, 0.4, 0.6, 1.0),
        (0.6, 0.2, 0.4, 1.0),
        (0.3, 0.6, 0.3, 1.0),
        (0.7, 0.4, 0.1, 1.0),
        (0.4, 0.3, 0.6, 1.0),
        (0.6, 0.3, 0.2, 1.0),
        (0.2, 0.5, 0.5, 1.0),
        (0.5, 0.2, 0.5, 1.0),
        (0.3, 0.3, 0.7, 1.0),
        (0.7, 0.2, 0.3, 1.0),
        (0.4, 0.5, 0.2, 1.0),
        (0.5, 0.3, 0.4, 1.0)
    ]

    # Plotting each bone
    for i, (bone_label, count, secondary_groups) in enumerate(primary_bones):
        plot_enhanced_category(ax, bone_label, count, positions, color_map[i % len(color_map)], secondary_groups)

    # FIXED: Use actual_total_issues which reflects ALL filtering including secondary selections
    ax.text(-13.3, 11.0, f"Total Issues Analyzed: {actual_total_issues}", fontsize=12,
            bbox=dict(facecolor='lightblue', alpha=0.7, boxstyle='round'))
    plt.title("Fishbone (Ishikawa) Diagram", fontsize=16, fontweight='bold', pad=25)
    plt.tight_layout()
    plt.show()


class AutocompleteCombobox(ttk.Combobox):
    def __init__(self, master=None, completion_list=None, min_chars_to_suggest=1, debounce_ms=100, **kwargs):
        super().__init__(master, **kwargs)
        self._completion_list = [str(x) for x in (completion_list or [])]
        self.min_chars_to_suggest = min_chars_to_suggest
        self.debounce_ms = debounce_ms
        self._after_id = None
        self.popup = None
        self.listbox = None

        self._norm_map = {s: s for s in self._completion_list}
        self.set_completion_list(self._completion_list)

        self.bind('<KeyRelease>', self._on_keyrelease)
        self.bind('<FocusOut>', self._hide_popup)
        self.bind('<Down>', self._on_down)

    def set_completion_list(self, completion_list):
        self._completion_list = sorted(list(map(str, completion_list)), key=str.lower)
        self._norm_map = {s: s for s in self._completion_list}
        self['values'] = self._completion_list

    def _on_keyrelease(self, event):
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        self._update_combobox_values()
        self._after_id = self.after(self.debounce_ms, self._update_popup)

    def _update_combobox_values(self):
        typed = self.get()
        if len(typed) >= self.min_chars_to_suggest:
            suggestions = self._fuzzy_matches(typed)
            self['values'] = suggestions
        else:
            self['values'] = self._completion_list

    def _normalize(self, s: str) -> str:
        return ''.join(ch for ch in s.lower() if ch.isalnum())

    def _fuzzy_matches(self, typed: str):
        if not typed:
            return list(self._completion_list)
        low = typed.lower()
        normlow = self._normalize(typed)
        starts = [s for s in self._completion_list if s.lower().startswith(low)]
        contains = [s for s in self._completion_list if (low in s.lower()) and (not s in starts)]
        norm_contains = [s for s in self._completion_list if (normlow in self._normalize(s)) and (s not in starts) and (s not in contains)]
        results = starts + contains + norm_contains
        return results[:20]

    def _update_popup(self):
        self._after_id = None
        typed = self.get()
        
        self._update_combobox_values()

        if len(typed) < self.min_chars_to_suggest:
            self._hide_popup()
            return

        suggestions = self._fuzzy_matches(typed)
        if not suggestions:
            self._hide_popup()
            return

        if self.popup is None or not tk.Toplevel.winfo_exists(self.popup):
            self.popup = tk.Toplevel(self)
            self.popup.wm_overrideredirect(True)
            self.listbox = tk.Listbox(self.popup, exportselection=False)
            self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.listbox.bind('<ButtonRelease-1>', self._on_popup_click)
            self.listbox.bind('<Return>', self._on_popup_return)
            self.listbox.bind('<Escape>', lambda e: self._hide_popup())
            self.listbox.bind('<Up>', self._listbox_up)
            self.listbox.bind('<Down>', self._listbox_down)

        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        width = max(self.winfo_width(), 200)
        self.popup.geometry(f"{width}x150+{x}+{y}")

        self.listbox.delete(0, tk.END)
        for s in suggestions:
            self.listbox.insert(tk.END, s)

        try:
            self.popup.deiconify()
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(0)
            self.listbox.activate(0)
            self.listbox.focus_set()
        except Exception:
            pass

    def _hide_popup(self, event=None):
        if self.popup is not None and tk.Toplevel.winfo_exists(self.popup):
            try:
                self.popup.destroy()
            except Exception:
                pass
        self.popup = None
        self.listbox = None

    def _on_popup_click(self, event):
        if self.listbox is None:
            return
        sel = self.listbox.curselection()
        if sel:
            value = self.listbox.get(sel[0])
            self.set(value)
        self._hide_popup()
        try:
            self.event_generate('<<ComboboxSelected>>')
        except Exception:
            pass

    def _on_popup_return(self, event):
        self._on_popup_click(event)

    def _on_down(self, event):
        if self.popup is None:
            self._update_popup()
        return 'break'

    def _listbox_up(self, event):
        if self.listbox:
            idxs = self.listbox.curselection()
            idx = idxs[0] if idxs else 0
            new = max(0, idx - 1)
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(new)
            self.listbox.activate(new)
            return 'break'

    def _listbox_down(self, event):
        if self.listbox:
            idxs = self.listbox.curselection()
            idx = idxs[0] if idxs else -1
            new = min(self.listbox.size() - 1, idx + 1)
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(new)
            self.listbox.activate(new)
            return 'break'


class BoneWidget(ttk.Frame):
    def __init__(self, parent, columns, remove_callback, get_df_callback, refresh_callback, bone_type="primary", widget_id=None):
        super().__init__(parent)
        self.columns = list(columns)
        self.get_df_callback = get_df_callback
        self.refresh_callback = refresh_callback
        self.remove_callback = remove_callback
        self.bone_type = bone_type
        self.widget_id = widget_id if widget_id else id(self)
        self.full_value_list = []
        self._displayed_indices = []
        self._search_after_id = None
        self._is_loading = False
        self._selection_preserved = False
        self.setup_widget()

    def setup_widget(self):
        if self.bone_type == "filter":
            label_text = "Filter Column:"
        elif self.bone_type == "primary":
            label_text = "Primary Bone Column:"
        elif self.bone_type == "secondary":
            label_text = "Secondary Column:"
        else:  # tertiary
            label_text = "Tertiary Column:"
            
        ttk.Label(self, text=label_text).grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        
        self.column_var = tk.StringVar()
        self.column_cb = AutocompleteCombobox(self, textvariable=self.column_var, width=25, 
                                            min_chars_to_suggest=1, debounce_ms=100)
        self.column_cb.set_completion_list(self.columns)
        self.column_cb.grid(row=0, column=1, padx=(0, 10))
        self.column_cb.bind('<<ComboboxSelected>>', lambda e: self.on_column_changed())

        ttk.Label(self, text="Top K:").grid(row=0, column=2, padx=(0, 5), sticky=tk.W)
        self.top_k_var = tk.StringVar(value="10")
        ttk.Combobox(self, textvariable=self.top_k_var, values=["5", "10", "15", "20", "All"], width=8).grid(row=0, column=3, padx=(0, 10))

        ttk.Label(self, text="Filter Values:").grid(row=1, column=0, padx=(0, 5), pady=(5, 0), sticky=tk.W)
        value_frame = ttk.Frame(self)
        value_frame.grid(row=1, column=1, columnspan=4, padx=(0, 10), pady=(5, 0), sticky=tk.W+tk.E)

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(value_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.TOP, anchor='w', pady=(0, 5))
        search_entry.bind('<KeyRelease>', self._on_search_keyrelease)

        self.values_listbox = tk.Listbox(value_frame, selectmode=tk.MULTIPLE, width=40, height=6, exportselection=False)
        self.values_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(value_frame, orient=tk.VERTICAL, command=self.values_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.values_listbox.config(yscrollcommand=scrollbar.set)

        self.values_listbox.bind('<<ListboxSelect>>', self.on_selection_changed)

        button_frame = ttk.Frame(self)
        button_frame.grid(row=1, column=5, padx=(0, 10), pady=(5, 0), sticky=tk.W+tk.E)
        
        ttk.Button(button_frame, text="Load Values", command=lambda: self.load_column_values(preserve_selection=True, preserve_search=True)).pack(pady=(0, 2))
        ttk.Button(button_frame, text="Select All", command=self.select_all_visible).pack(pady=(2, 0))
        
        ttk.Button(self, text="Remove", command=lambda: self.remove_callback(self)).grid(row=0, column=6, rowspan=2, padx=(10, 0))

    def select_all_visible(self):
        if self.values_listbox.size() > 0:
            self._is_loading = True
            self.values_listbox.selection_set(0, tk.END)
            self._is_loading = False
            self.on_selection_changed()

    def update_completion_list(self, columns):
        self.columns = list(columns)
        self.column_cb.set_completion_list(self.columns)

    def on_column_changed(self):
        self.values_listbox.delete(0, tk.END)
        self.full_value_list = []
        self._displayed_indices = []
        try:
            self.load_column_values(preserve_selection=False, preserve_search=False)
        except Exception:
            pass

    def on_selection_changed(self, event=None):
        if not self._is_loading and not self._selection_preserved:
            try:
                self.refresh_callback(self)
            except Exception:
                pass

    def _on_search_keyrelease(self, event):
        if self._search_after_id:
            try:
                self.after_cancel(self._search_after_id)
            except Exception:
                pass
        self._search_after_id = self.after(150, self._apply_search_filter)

    def _apply_search_filter(self):
        self._search_after_id = None
        q = self.search_var.get().strip().lower()
        
        # Preserve selections during search
        prior_selections = []
        if self.values_listbox.size() > 0:
            for i in self.values_listbox.curselection():
                display = self.values_listbox.get(i)
                for d, orig in self.full_value_list:
                    if d == display:
                        prior_selections.append(orig)
                        break
        
        self.values_listbox.delete(0, tk.END)
        self._displayed_indices = []
        if not self.full_value_list:
            return
            
        for idx, (display, orig) in enumerate(self.full_value_list):
            if not q or q in display.lower() or q in str(orig).lower():
                self.values_listbox.insert(tk.END, display)
                self._displayed_indices.append(idx)
        
        # Restore selections after search
        if prior_selections:
            self._is_loading = True
            for i, (display, orig) in enumerate(self.full_value_list):
                if orig in prior_selections:
                    try:
                        vis_idx = self._displayed_indices.index(i)
                        self.values_listbox.selection_set(vis_idx)
                    except Exception:
                        pass
            self._is_loading = False

    def load_column_values(self, preserve_selection=False, preserve_search=False):
        column = self.column_var.get().strip()
        if not column:
            messagebox.showwarning("No Column", "Please select a column first.")
            return
            
        current_search = self.search_var.get() if preserve_search else ""
        
        self._is_loading = True
        self._selection_preserved = True
        
        try:
            df = self.get_df_callback(exclude_widget=self)
        except TypeError:
            df = self.get_df_callback()

        self.values_listbox.delete(0, tk.END)
        prior_selected_orig = []
        if preserve_selection and self.full_value_list:
            for i in self.values_listbox.curselection():
                display = self.values_listbox.get(i)
                for d, orig in self.full_value_list:
                    if d == display:
                        prior_selected_orig.append(orig)
                        break

        self.full_value_list = []
        self._displayed_indices = []
        
        if not preserve_search:
            self.search_var.set('')

        if df is None:
            self.values_listbox.insert(tk.END, "No data loaded")
            self._is_loading = False
            self._selection_preserved = False
            return

        if column not in df.columns:
            normalized_columns = {normalize_col_name(col): col for col in df.columns}
            normalized_input = normalize_col_name(column)
            if normalized_input in normalized_columns:
                column = normalized_columns[normalized_input]
                self.column_var.set(column)
            else:
                self.values_listbox.insert(tk.END, f"Column '{column}' not found")
                self._is_loading = False
                self._selection_preserved = False
                return

        top_k_str = self.top_k_var.get()
        top_k = 0 if top_k_str == "All" else int(top_k_str)
        value_counts = df[column].value_counts(dropna=False)
        if top_k > 0:
            value_counts = value_counts.head(top_k)

        for val, cnt in value_counts.items():
            if pd.isna(val):
                display = f"<NaN>  ({cnt})"
                orig = np.nan
            else:
                display = f"{val}  ({cnt})"
                orig = val
            self.full_value_list.append((display, orig))

        total_unique = df[column].nunique(dropna=False)
        if top_k > 0 and total_unique > top_k:
            extra_text = f"... ({total_unique - top_k} more values not shown)"
            self.full_value_list.append((extra_text, None))

        for idx, (display, orig) in enumerate(self.full_value_list):
            self.values_listbox.insert(tk.END, display)
            self._displayed_indices.append(idx)

        if preserve_selection and prior_selected_orig:
            for i, (display, orig) in enumerate(self.full_value_list):
                if orig in prior_selected_orig:
                    try:
                        vis_idx = self._displayed_indices.index(i)
                        self.values_listbox.selection_set(vis_idx)
                    except Exception:
                        pass

        if preserve_search and current_search:
            self.search_var.set(current_search)
            self._apply_search_filter()
        
        self._is_loading = False
        self._selection_preserved = False

    def get_config(self):
        top_k_str = self.top_k_var.get()
        top_k = 0 if top_k_str == "All" else int(top_k_str)
        selected_values = []
        if self.values_listbox.size() > 0:
            for i in self.values_listbox.curselection():
                try:
                    full_idx = self._displayed_indices[i]
                except Exception:
                    item = self.values_listbox.get(i)
                    full_idx = None
                    for j, (display, orig) in enumerate(self.full_value_list):
                        if display == item:
                            full_idx = j
                            break
                if full_idx is None:
                    continue
                display, orig = self.full_value_list[full_idx]
                if isinstance(orig, float) and np.isnan(orig):
                    selected_values.append(np.nan)
                else:
                    selected_values.append(orig)

        return {
            'column': self.column_var.get().strip(),
            'values': selected_values,
            'top_k': top_k,
            'type': self.bone_type,
            'widget_id': self.widget_id
        }

# GUI 

class FishboneConfigurator:
    def __init__(self, root):
        self.root = root
        self.root.title("Fishbone Diagram Configurator")
        self.root.geometry("1100x850")

        self.selected_file = {"path": None}
        self.df = None
        self.columns = []
        self.bone_configs = []
        self.problem_column = None
        self.problem_value = None
        self.secondary_widgets_order = []
        self.tertiary_widgets_order = []
        self._refreshing = False

        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        container = ttk.Frame(main_frame)
        container.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        def _on_linux_scroll_up(event):
            canvas.yview_scroll(-1, "units")
            
        def _on_linux_scroll_down(event):
            canvas.yview_scroll(1, "units")

        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Button-4>", _on_linux_scroll_up)
        canvas.bind("<Button-5>", _on_linux_scroll_down)
        
        self.scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        self.scrollable_frame.bind("<Button-4>", _on_linux_scroll_up)
        self.scrollable_frame.bind("<Button-5>", _on_linux_scroll_down)

        # File selection
        file_frame = ttk.LabelFrame(self.scrollable_frame, text="File Selection", padding="5")
        file_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(file_frame, text="Choose Excel File...", command=self.choose_file).pack(side=tk.LEFT)
        self.file_label = ttk.Label(file_frame, text="No file selected")
        self.file_label.pack(side=tk.LEFT, padx=(10, 0))

        sheet_frame = ttk.Frame(file_frame)
        sheet_frame.pack(side=tk.RIGHT)
        ttk.Label(sheet_frame, text="Sheet:").pack(side=tk.LEFT)
        self.sheet_var = tk.StringVar(value="0")
        ttk.Entry(sheet_frame, textvariable=self.sheet_var, width=10).pack(side=tk.LEFT, padx=(5, 0))

        # Problem statement selection
        self.problem_frame = ttk.LabelFrame(self.scrollable_frame, text="Problem Statement Selection", padding="5")
        self.problem_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(self.problem_frame, text="Problem Column:").pack(side=tk.LEFT)
        self.problem_column_var = tk.StringVar()
        self.problem_column_cb = AutocompleteCombobox(self.problem_frame, textvariable=self.problem_column_var, 
                                                    width=25, min_chars_to_suggest=1, debounce_ms=100)
        self.problem_column_cb.pack(side=tk.LEFT, padx=(5, 10))
        self.problem_column_cb.bind('<<ComboboxSelected>>', self.on_problem_column_selected)
        
        ttk.Label(self.problem_frame, text="Problem Value:").pack(side=tk.LEFT)
        self.problem_value_var = tk.StringVar()
        self.problem_value_cb = AutocompleteCombobox(self.problem_frame, textvariable=self.problem_value_var, 
                                                   width=25, min_chars_to_suggest=1, debounce_ms=100)
        self.problem_value_cb.pack(side=tk.LEFT, padx=(5, 0))
        self.problem_value_cb.bind('<<ComboboxSelected>>', self.on_problem_value_selected)

        # Filter configuration
        self.filter_frame = ttk.LabelFrame(self.scrollable_frame, text="Data Filters (Optional)", padding="5")
        self.filter_frame.pack(fill=tk.X, pady=(0, 10))
        self.filter_bone_frame = ttk.Frame(self.filter_frame)
        self.filter_bone_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Button(self.filter_frame, text="Add Filter Column", command=lambda: self.add_bone_widget("filter")).pack(pady=5)

        # Primary bones configuration
        self.primary_frame = ttk.LabelFrame(self.scrollable_frame, text="Primary Bones Configuration", padding="5")
        self.primary_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.primary_bone_frame = ttk.Frame(self.primary_frame)
        self.primary_bone_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Button(self.primary_frame, text="Add Primary Bone Column", command=lambda: self.add_bone_widget("primary")).pack(pady=5)

        # Secondary columns configuration
        self.secondary_frame = ttk.LabelFrame(self.scrollable_frame, text="Secondary Columns (Hierarchical Sub-branches)", padding="5")
        self.secondary_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.secondary_bone_frame = ttk.Frame(self.secondary_frame)
        self.secondary_bone_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Button(self.secondary_frame, text="Add Secondary Column", command=lambda: self.add_bone_widget("secondary")).pack(pady=5)

        # TERTIARY COLUMNS CONFIGURATION
        self.tertiary_frame = ttk.LabelFrame(self.scrollable_frame, text="Tertiary Columns (Nested under Secondary)", padding="5")
        self.tertiary_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.tertiary_bone_frame = ttk.Frame(self.tertiary_frame)
        self.tertiary_bone_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Button(self.tertiary_frame, text="Add Tertiary Column", command=lambda: self.add_bone_widget("tertiary")).pack(pady=5)

        # Head label
        head_frame = ttk.Frame(self.scrollable_frame)
        head_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(head_frame, text="Head Label:").pack(side=tk.LEFT)
        self.head_label_var = tk.StringVar(value="Select a problem value above")
        ttk.Entry(head_frame, textvariable=self.head_label_var, width=50).pack(side=tk.LEFT, padx=(10, 0))

        # Generating button
        ttk.Button(self.scrollable_frame, text="Generate Fishbone", command=self.generate_fishbone).pack(pady=10)

    def choose_file(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files", ".xls;.xlsx;.xlsm"), ("All files",".*")])
        if path:
            self.selected_file["path"] = path
            self.file_label.config(text=path.split('/')[-1])
            self.load_file_data()

    def load_file_data(self):
        try:
            sheet_val = self.sheet_var.get()
            if sheet_val.isdigit():
                sheet_val = int(sheet_val)

            self.df, _ = load_data_from_excel(self.selected_file["path"], sheet_name=sheet_val, print_diagnostics=False)
            self.columns = list(self.df.columns)
            self.problem_column_cb.set_completion_list(self.columns)
            self.problem_value_cb.set_completion_list([])

            for frame in [self.filter_bone_frame, self.primary_bone_frame, self.secondary_bone_frame, self.tertiary_bone_frame]:
                for w in frame.winfo_children():
                    if isinstance(w, BoneWidget):
                        w.update_completion_list(self.columns)
            print(f"Loaded file with {len(self.df)} rows and {len(self.columns)} columns")

        except Exception as e:
            messagebox.showerror("Error loading file", f"Could not read Excel file: {e}")

    def on_problem_column_selected(self, event):
        column = self.problem_column_var.get().strip()
        if column and self.df is not None and column in self.df.columns:
            values = sorted(self.df[column].dropna().astype(str).unique())
            self.problem_value_cb.set_completion_list(values)

    def on_problem_value_selected(self, event):
        problem_value = self.problem_value_var.get().strip()
        if problem_value:
            self.head_label_var.set(problem_value)
            self.problem_value = problem_value
            self.problem_column = self.problem_column_var.get().strip()
            self.refresh_dependent_lists()
            self.update_head_label()

    def add_bone_widget(self, bone_type="primary"):
        if self.df is None:
            messagebox.showwarning("No Data", "Please load a file first.")
            return
            
        if bone_type == "filter":
            parent_frame = self.filter_bone_frame
            widget_id = None
        elif bone_type == "primary":
            parent_frame = self.primary_bone_frame
            widget_id = None
        elif bone_type == "secondary":
            parent_frame = self.secondary_bone_frame
            widget_id = len(self.secondary_widgets_order)
            self.secondary_widgets_order.append(widget_id)
        else:  # tertiary
            parent_frame = self.tertiary_bone_frame
            widget_id = len(self.tertiary_widgets_order)
            self.tertiary_widgets_order.append(widget_id)
            
        bone_widget = BoneWidget(parent_frame, self.columns, self.remove_bone_widget,
                                 get_df_callback=self.get_filtered_df,
                                 refresh_callback=self.refresh_dependent_lists,
                                 bone_type=bone_type,
                                 widget_id=widget_id)
        bone_widget.pack(fill=tk.X, pady=5)

    def remove_bone_widget(self, widget):
        if widget.bone_type == 'secondary' and hasattr(widget, 'widget_id'):
            if widget.widget_id in self.secondary_widgets_order:
                self.secondary_widgets_order.remove(widget.widget_id)
        elif widget.bone_type == 'tertiary' and hasattr(widget, 'widget_id'):
            if widget.widget_id in self.tertiary_widgets_order:
                self.tertiary_widgets_order.remove(widget.widget_id)
        
        widget.destroy()
        self.refresh_dependent_lists()
        self.update_head_label()

    def update_head_label(self):
        if self.problem_value:
            head_label = self.problem_value
            
            filter_values = []
            for widget in self.filter_bone_frame.winfo_children():
                if isinstance(widget, BoneWidget):
                    config = widget.get_config()
                    if config['column'] and config['values']:
                        for value in config['values']:
                            if pd.isna(value):
                                filter_values.append("<NaN>")
                            else:
                                filter_values.append(str(value))
            
            if filter_values:
                if len(filter_values) > 5:
                    display_values = ", ".join(filter_values[:5]) + f"... (+{len(filter_values) - 5} more)"
                else:
                    display_values = ", ".join(filter_values)
                head_label += f"\n({display_values})"
            
            self.head_label_var.set(head_label)

    def generate_fishbone(self):
        if not self.selected_file["path"]:
            messagebox.showwarning("No file selected", "Please choose an Excel file first.")
            return

        self.update_head_label()
        head_label = self.head_label_var.get()

        self.bone_configs = []
        
        for widget in self.filter_bone_frame.winfo_children():
            if isinstance(widget, BoneWidget):
                config = widget.get_config()
                if config['column']:
                    self.bone_configs.append(config)

        for widget in self.primary_bone_frame.winfo_children():
            if isinstance(widget, BoneWidget):
                config = widget.get_config()
                if config['column'] and config['column'] != self.problem_column:
                    self.bone_configs.append(config)

        # Add secondary columns in hierarchical order
        secondary_configs = []
        for widget in self.secondary_bone_frame.winfo_children():
            if isinstance(widget, BoneWidget):
                config = widget.get_config()
                if config['column']:
                    secondary_configs.append(config)
        
        # Sort by widget_id to maintain hierarchy order
        secondary_configs.sort(key=lambda x: x.get('widget_id', 0))
        self.bone_configs.extend(secondary_configs)

        # Add tertiary columns in hierarchical order
        tertiary_configs = []
        for widget in self.tertiary_bone_frame.winfo_children():
            if isinstance(widget, BoneWidget):
                config = widget.get_config()
                if config['column']:
                    tertiary_configs.append(config)
        
        # Sort by widget_id to maintain hierarchy order
        tertiary_configs.sort(key=lambda x: x.get('widget_id', 0))
        self.bone_configs.extend(tertiary_configs)

        if self.problem_column and (self.problem_value is not None) and self.df is not None:
            try:
                mask = self.df[self.problem_column].astype(str) == str(self.problem_value)
                original_vals = list(self.df.loc[mask, self.problem_column].unique())
                if not original_vals:
                    original_vals = [self.problem_value]
                self.bone_configs.insert(0, {
                    'column': self.problem_column,
                    'values': original_vals,
                    'top_k': 0,
                    'type': 'filter'
                })
            except Exception:
                self.bone_configs.insert(0, {
                    'column': self.problem_column,
                    'values': [self.problem_value],
                    'top_k': 0,
                    'type': 'filter'
                })

        if not any(config['type'] == 'primary' for config in self.bone_configs):
            messagebox.showwarning("No Primary Bones", "Please add at least one primary bone column.")
            return

        try:
            sheet_val = self.sheet_var.get()
            if sheet_val.isdigit():
                sheet_val = int(sheet_val)

            create_enhanced_fishbone_from_excel(self.selected_file["path"], self.bone_configs, head_label, sheet_name=sheet_val)
        except Exception as e:
            messagebox.showerror("Plotting error", f"An error occurred while creating the fishbone: {e}")

    def get_filtered_df(self, exclude_widget=None):
        """
        Returns dataframe filtered hierarchically based on widget positions
        """
        if self.df is None:
            return None
        
        df = self.df.copy()

        # Apply problem-level filter
        if self.problem_column and self.problem_value is not None:
            if self.problem_column in df.columns:
                df = df[df[self.problem_column].astype(str) == str(self.problem_value)]

        # Apply filter widgets
        for w in self.filter_bone_frame.winfo_children():
            if isinstance(w, BoneWidget) and w is not exclude_widget:
                cfg = w.get_config()
                col = cfg['column']
                vals = cfg['values']
                if col and vals and col in df.columns:
                    if any(pd.isna(v) for v in vals):
                        non_nans = [v for v in vals if not pd.isna(v)]
                        mask = df[col].isin(non_nans) | df[col].isna()
                        df = df[mask]
                    else:
                        df = df[df[col].isin(vals)]

        # Apply primary bone selections
        for w in self.primary_bone_frame.winfo_children():
            if isinstance(w, BoneWidget) and w is not exclude_widget:
                cfg = w.get_config()
                col = cfg['column']
                vals = cfg['values']
                if col and vals and col in df.columns:
                    if any(pd.isna(v) for v in vals):
                        non_nans = [v for v in vals if not pd.isna(v)]
                        mask = df[col].isin(non_nans) | df[col].isna()
                        df = df[mask]
                    else:
                        df = df[df[col].isin(vals)]

        # Apply secondary bone selections in hierarchical order
        secondary_widgets = [w for w in self.secondary_bone_frame.winfo_children() 
                           if isinstance(w, BoneWidget) and w is not exclude_widget]
        
        # Sort by widget_id to maintain hierarchy
        secondary_widgets.sort(key=lambda w: getattr(w, 'widget_id', 0))
        
        for w in secondary_widgets:
            cfg = w.get_config()
            col = cfg['column']
            vals = cfg['values']
            if col and vals and col in df.columns:
                if any(pd.isna(v) for v in vals):
                    non_nans = [v for v in vals if not pd.isna(v)]
                    mask = df[col].isin(non_nans) | df[col].isna()
                    df = df[mask]
                else:
                    df = df[df[col].isin(vals)]

        # Apply tertiary bone selections in hierarchical order
        tertiary_widgets = [w for w in self.tertiary_bone_frame.winfo_children() 
                          if isinstance(w, BoneWidget) and w is not exclude_widget]
        
        # Sort by widget_id to maintain hierarchy
        tertiary_widgets.sort(key=lambda w: getattr(w, 'widget_id', 0))
        
        for w in tertiary_widgets:
            cfg = w.get_config()
            col = cfg['column']
            vals = cfg['values']
            if col and vals and col in df.columns:
                if any(pd.isna(v) for v in vals):
                    non_nans = [v for v in vals if not pd.isna(v)]
                    mask = df[col].isin(non_nans) | df[col].isna()
                    df = df[mask]
                else:
                    df = df[df[col].isin(vals)]

        return df

    def refresh_dependent_lists(self, changed_widget=None):
        """
        Smart refresh that prevents recursive refreshes and preserves selections properly
        """
        if self._refreshing:
            return
            
        self._refreshing = True
        
        try:
            if changed_widget is None:
                # Refresh all secondary and tertiary widgets
                frames_to_refresh = [self.secondary_bone_frame, self.tertiary_bone_frame]
            else:
                if changed_widget.bone_type == 'filter':
                    frames_to_refresh = [self.primary_bone_frame, self.secondary_bone_frame, self.tertiary_bone_frame]
                elif changed_widget.bone_type == 'primary':
                    frames_to_refresh = [self.secondary_bone_frame, self.tertiary_bone_frame]
                elif changed_widget.bone_type == 'secondary':
                    # For secondary widgets, refresh tertiary widgets that come after
                    frames_to_refresh = [self.tertiary_bone_frame]
                else:
                    # For tertiary widgets, no need to refresh anything else
                    frames_to_refresh = []
            
            for frame in frames_to_refresh:
                for w in frame.winfo_children():
                    if isinstance(w, BoneWidget) and w is not changed_widget:
                        # For hierarchical widgets, only refresh those that come AFTER in hierarchy
                        if w.bone_type == 'secondary' and changed_widget and changed_widget.bone_type == 'secondary':
                            if getattr(w, 'widget_id', 0) <= getattr(changed_widget, 'widget_id', 0):
                                continue
                        elif w.bone_type == 'tertiary' and changed_widget and changed_widget.bone_type == 'tertiary':
                            if getattr(w, 'widget_id', 0) <= getattr(changed_widget, 'widget_id', 0):
                                continue
                        
                        if w.column_var.get().strip():
                            try:
                                w.load_column_values(preserve_selection=True, preserve_search=True)
                            except Exception:
                                pass
            
            self.update_head_label()
        finally:
            self._refreshing = False

# Main

def main():
    root = tk.Tk()
    app = FishboneConfigurator(root)
    root.mainloop()

if __name__ == "__main__":
    main()
