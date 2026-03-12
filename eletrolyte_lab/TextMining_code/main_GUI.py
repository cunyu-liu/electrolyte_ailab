import tkinter as tk
from tkinter import ttk, scrolledtext, font, messagebox
from datetime import datetime
import threading
import time
import platform
import subprocess
import sys
import os

# Add the path to query_search_entities.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class ChatApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("Chemist Chatbot App")
        self.root.geometry("800x600")
        
        # Detect platform
        self.is_mac = platform.system() == 'Darwin'
        
        # Configure the color scheme
        self.bg_color = "#2D1B4F"  # Dark low saturation purple
        self.menu_bg = "#3A245F"   # Slightly lighter purple for menu
        self.main_panel_bg = "#FFFFFF"  # White for conversation panel
        self.text_color = "#333333"
        self.accent_color = "#7E5BFF"
        
        # Message bubble colors
        self.user_msg_bg = "#4A2F7F"      # Dark purple background for user messages
        self.user_msg_fg = "#FFFFFF"      # White text for user messages
        self.ai_msg_bg = "#E8EAF6"        # Low saturation blue for AI messages
        self.ai_msg_fg = "#333333"        # Dark text for AI messages
        
        # Button colors - improved contrast
        self.button_color = "#6A4CFF"
        self.button_hover = "#7D5FFF"
        self.button_active = "#5A3FE6"
        self.button_disabled = "#9D9D9D"  # Darker gray for disabled state
        
        # Quit button colors - improved contrast
        self.quit_button_bg = "#FF5555"   # Red for quit button
        self.quit_button_hover = "#FF7777"
        self.quit_button_active = "#DD4444"
        
        self.input_bg = "#F8F9FA"
        
        self.root.configure(bg=self.bg_color)
        
        # AI response state
        self.waiting_for_ai = False
        self.send_button = None
        self.quit_button = None
        
        # Processing state
        self.processing_message_id = None
        self.processing_animation_index = 0
        self.processing_animation_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        
        # Set up the main structure
        self.setup_menu_bar()
        self.setup_conversation_panel()
        self.setup_input_area()
        
        # Sample conversation data
        self.conversation_history = [
            {"sender": "ai", "message": "Hello! Welcome to the ChemMind Chatbot. How can I help you today?", "time": "10:00 AM"},
            {"sender": "user", "message": "Hi! I'm Java. Please recommendate the chemical electrolytes based on my query", "time": "10:01 AM"},
        ]
        
        # Display initial conversation
        self.display_conversation()
    
    def setup_menu_bar(self):
        """Create the top menu bar with quit button"""
        menu_frame = tk.Frame(self.root, bg=self.menu_bg, height=50)
        menu_frame.pack(fill=tk.X)
        menu_frame.pack_propagate(False)
        
        # App title/logo
        title_label = tk.Label(
            menu_frame, 
            text="ChemMind Chatbot", 
            font=("Arial", 16, "bold"),
            bg=self.menu_bg,
            fg="#FFFFFF",
            padx=20
        )
        title_label.pack(side=tk.LEFT)
        
        # Quit button (X icon) on top right
        self.quit_button = tk.Button(
            menu_frame,
            text="✕",
            font=("Arial", 16, "bold"),
            bg=self.quit_button_bg,
            fg="#797171",
            activebackground=self.quit_button_active,
            activeforeground="#7C7683",
            bd=0,
            cursor="hand2",
            padx=15,
            pady=2,
            command=self.confirm_quit
        )
        self.quit_button.pack(side=tk.RIGHT)
        
        # Bind hover events for quit button
        self.quit_button.bind("<Enter>", lambda e: self.quit_button.config(bg=self.quit_button_hover))
        self.quit_button.bind("<Leave>", lambda e: self.quit_button.config(bg=self.quit_button_bg))
        
        # Add a separator
        separator = tk.Frame(self.root, bg="#4A2F7F", height=2)
        separator.pack(fill=tk.X)
    
    def confirm_quit(self):
        """Ask for confirmation before quitting"""
        if messagebox.askyesno("Quit", "Are you sure you want to quit?"):
            self.root.quit()
    
    def setup_conversation_panel(self):
        """Create the main conversation display panel with enhanced scrolling"""
        # Frame for conversation panel
        conversation_frame = tk.Frame(self.root, bg=self.main_panel_bg)
        conversation_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(15, 10))
        
        # Add a label for the conversation
        panel_label = tk.Label(
            conversation_frame,
            text="Conversation",
            font=("Arial", 12, "bold"),
            bg=self.main_panel_bg,
            fg=self.text_color,
            anchor="w"
        )
        panel_label.pack(fill=tk.X, pady=(0, 10))
        
        # Create a frame with scrollbar for the conversation
        self.create_scrollable_conversation(conversation_frame)
    
    def create_scrollable_conversation(self, parent_frame):
        """Create a scrollable conversation area with multiple scrolling methods"""
        # Create main container
        container = tk.Frame(parent_frame, bg=self.main_panel_bg)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Create a canvas
        self.canvas = tk.Canvas(container, bg=self.main_panel_bg, highlightthickness=0)
        
        # Create vertical scrollbar
        v_scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        
        # Create horizontal scrollbar (hidden by default, can be enabled if needed)
        h_scrollbar = ttk.Scrollbar(container, orient="horizontal", command=self.canvas.xview)
        
        # Configure canvas scrolling
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Create a frame inside the canvas
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.main_panel_bg)
        
        # Add the frame to the canvas
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Configure frame to update canvas scrollregion
        self.scrollable_frame.bind("<Configure>", self.on_frame_configure)
        
        # Configure canvas to resize with window
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        
        # Pack the scrollbars and canvas
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind scrolling events
        self.bind_scroll_events()
        
        # Initially hide horizontal scrollbar
        h_scrollbar.pack_forget()
    
    def on_frame_configure(self, event=None):
        """Reset the scroll region to encompass the inner frame"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def on_canvas_configure(self, event):
        """Reset the canvas window width when canvas is resized"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def bind_scroll_events(self):
        """Bind various scrolling events for different input methods"""
        
        # Mouse wheel scrolling (Windows/Linux)
        def on_mousewheel(event):
            if event.num == 5 or event.delta == -120:
                self.canvas.yview_scroll(1, "units")
            if event.num == 4 or event.delta == 120:
                self.canvas.yview_scroll(-1, "units")
        
        # For Windows/Linux with mouse wheel
        self.canvas.bind_all("<MouseWheel>", on_mousewheel)
        self.canvas.bind_all("<Button-4>", on_mousewheel)
        self.canvas.bind_all("<Button-5>", on_mousewheel)
        
        # For Mac trackpad gestures - two-finger scroll
        def on_mac_scroll(event):
            # Mac trackpad sends different events
            if self.is_mac:
                # Handle trackpad scrolling
                if hasattr(event, 'delta'):
                    # Some Mac setups use delta
                    self.canvas.yview_scroll(int(-1*(event.delta)), "units")
                else:
                    # Default scroll for Mac
                    self.canvas.yview_scroll(int(-event.delta_y), "units")
                return "break"
        
        # Bind for Mac trackpad
        self.canvas.bind_all("<B2-Motion>", on_mac_scroll)
        self.canvas.bind_all("<Button-2>", lambda e: "break")
        
        # Additional Mac-specific bindings
        if self.is_mac:
            # Try alternative bindings for Mac trackpad
            self.canvas.bind_all("<Motion>", self.on_mac_trackpad_motion)
        
        # Keyboard scrolling (arrow keys, page up/down)
        def on_key_scroll(event):
            if event.keysym == "Up":
                self.canvas.yview_scroll(-1, "units")
            elif event.keysym == "Down":
                self.canvas.yview_scroll(1, "units")
            elif event.keysym == "Page_Up":
                self.canvas.yview_scroll(-5, "pages")
            elif event.keysym == "Page_Down":
                self.canvas.yview_scroll(5, "pages")
            elif event.keysym == "Home":
                self.canvas.yview_moveto(0)
            elif event.keysym == "End":
                self.canvas.yview_moveto(1)
        
        # Bind keyboard scrolling when canvas has focus
        self.canvas.bind("<Up>", on_key_scroll)
        self.canvas.bind("<Down>", on_key_scroll)
        self.canvas.bind("<Prior>", on_key_scroll)
        self.canvas.bind("<Next>", on_key_scroll)
        self.canvas.bind("<Home>", on_key_scroll)
        self.canvas.bind("<End>", on_key_scroll)
        
        # Also allow scrolling when mouse is over the scrollable frame
        self.scrollable_frame.bind("<Enter>", lambda e: self.canvas.focus_set())
        
        # Add scrollbar dragging
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        
        # Enable canvas to receive focus for keyboard scrolling
        self.canvas.configure(takefocus=1)
        self.canvas.focus_set()
    
    def on_mac_trackpad_motion(self, event):
        """Handle Mac trackpad motion for scrolling"""
        pass
    
    def on_mouse_drag(self, event):
        """Handle mouse dragging for scrolling"""
        self.canvas.scan_dragto(event.x, event.y, gain=1)
    
    def on_mouse_press(self, event):
        """Handle mouse press for dragging"""
        self.canvas.scan_mark(event.x, event.y)
    
    def display_conversation(self):
        """Display the conversation history in the main panel"""
        # Clear existing messages
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Add each message
        for msg in self.conversation_history:
            self.add_message_bubble(msg["sender"], msg["message"], msg["time"])
        
        # Update canvas scroll region
        self.on_frame_configure()
        
        # Scroll to bottom
        self.root.after(100, self.scroll_to_bottom)
    
    def add_message_bubble(self, sender, message, timestamp):
        """Add a message bubble with proper alignment and styling"""
        # Create frame for the entire message (timestamp + bubble)
        message_frame = tk.Frame(self.scrollable_frame, bg=self.main_panel_bg)
        message_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Configure alignment based on sender
        if sender == "user":
            # User messages on the right
            alignment_frame = tk.Frame(message_frame, bg=self.main_panel_bg)
            alignment_frame.pack(anchor="e", padx=(100, 0))
            
            # Timestamp (right aligned)
            time_label = tk.Label(
                alignment_frame,
                text=timestamp,
                font=("Arial", 9),
                bg=self.main_panel_bg,
                fg="#666666",
                anchor="e"
            )
            time_label.pack(fill=tk.X, anchor="e")
            
            # Message bubble
            bubble_frame = tk.Frame(alignment_frame, bg=self.user_msg_bg, relief=tk.FLAT)
            bubble_frame.pack(anchor="e", pady=(2, 0))
            
            # Message text
            message_label = tk.Label(
                bubble_frame,
                text=message,
                font=("Arial", 11),
                bg=self.user_msg_bg,
                fg=self.user_msg_fg,
                wraplength=400,
                justify=tk.LEFT,
                padx=12,
                pady=8
            )
            message_label.pack()
            
        elif sender == "ai":
            # AI messages on the left
            alignment_frame = tk.Frame(message_frame, bg=self.main_panel_bg)
            alignment_frame.pack(anchor="w", padx=(0, 100))
            
            # Timestamp (left aligned)
            time_label = tk.Label(
                alignment_frame,
                text=timestamp,
                font=("Arial", 9),
                bg=self.main_panel_bg,
                fg="#666666",
                anchor="w"
            )
            time_label.pack(fill=tk.X, anchor="w")
            
            # Message bubble
            bubble_frame = tk.Frame(alignment_frame, bg=self.ai_msg_bg, relief=tk.FLAT)
            bubble_frame.pack(anchor="w", pady=(2, 0))
            
            # Message text
            message_label = tk.Label(
                bubble_frame,
                text=message,
                font=("Arial", 11),
                bg=self.ai_msg_bg,
                fg=self.ai_msg_fg,
                wraplength=400,
                justify=tk.LEFT,
                padx=12,
                pady=8
            )
            message_label.pack()
            
        elif sender == "processing":
            # Processing messages on the left (centered)
            alignment_frame = tk.Frame(message_frame, bg=self.main_panel_bg)
            alignment_frame.pack(anchor="center", padx=100)
            
            # No timestamp for processing messages
            
            # Message bubble
            bubble_frame = tk.Frame(alignment_frame, bg=self.ai_msg_bg, relief=tk.FLAT)
            bubble_frame.pack(anchor="center", pady=(2, 0))
            
            # Message text (centered)
            message_label = tk.Label(
                bubble_frame,
                text=message,
                font=("Arial", 11),
                bg=self.ai_msg_bg,
                fg=self.ai_msg_fg,
                wraplength=400,
                justify=tk.CENTER,
                padx=20,
                pady=10
            )
            message_label.pack()
    
    def scroll_to_bottom(self):
        """Scroll the canvas to show the latest message"""
        self.canvas.yview_moveto(1.0)
    
    def setup_input_area(self):
        """Create the input area with message box and send button at the bottom"""
        # Frame for the entire input area
        input_frame = tk.Frame(self.root, bg=self.bg_color)
        input_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Inner frame for better styling
        input_inner_frame = tk.Frame(input_frame, bg=self.input_bg, relief=tk.FLAT, bd=1)
        input_inner_frame.pack(fill=tk.BOTH, expand=True)
        
        # Message entry box
        self.message_entry = tk.Text(
            input_inner_frame,
            height=3,
            wrap=tk.WORD,
            bg="#FFFFFF",
            fg=self.text_color,
            font=("Arial", 11),
            padx=12,
            pady=8,
            bd=0,
            highlightthickness=1,
            highlightbackground="#CCCCCC",
            highlightcolor=self.accent_color,
            insertbackground=self.accent_color
        )
        self.message_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.message_entry.bind("<Return>", self.on_enter_pressed)
        self.message_entry.bind("<Key>", self.on_key_press)
        
        # Send button frame for better alignment
        send_frame = tk.Frame(input_inner_frame, bg=self.input_bg)
        send_frame.pack(side=tk.RIGHT, padx=(0, 10), pady=10)
        
        # Send button with arrow icon
        self.send_button = tk.Button(
            send_frame,
            text="➤",
            font=("Arial", 16, "bold"),
            bg=self.button_color,
            fg="#707378",
            activebackground=self.button_active,
            activeforeground="#493C6A",
            bd=0,
            cursor="hand2",
            width=3,
            height=1,
            command=self.send_message,
            state=tk.NORMAL
        )
        self.send_button.pack()
        
        # Bind hover events for send button
        self.send_button.bind("<Enter>", lambda e: self.send_button.config(bg=self.button_hover))
        self.send_button.bind("<Leave>", lambda e: self.send_button.config(bg=self.button_color))
        
        # Add hint text
        hint_label = tk.Label(
            send_frame,
            text="Send",
            font=("Arial", 9),
            bg=self.input_bg,
            fg="#666666"
        )
        hint_label.pack(pady=(5, 0))
        
        # Add placeholder text
        self.message_entry.insert(1.0, "Type your message here...")
        self.message_entry.bind("<FocusIn>", self.clear_placeholder)
        self.message_entry.bind("<FocusOut>", self.restore_placeholder)
        
        # Set initial placeholder state
        self.placeholder_active = True
        self.message_entry.config(fg="#999999")
    
    def on_key_press(self, event):
        """Handle key press events to track when user starts typing"""
        if self.placeholder_active and event.keysym not in ['Shift_L', 'Shift_R', 'Control_L', 'Control_R']:
            self.clear_placeholder()
    
    def clear_placeholder(self, event=None):
        """Clear placeholder text when entry is focused"""
        if self.placeholder_active:
            self.message_entry.delete(1.0, tk.END)
            self.message_entry.config(fg=self.text_color)
            self.placeholder_active = False
    
    def restore_placeholder(self, event=None):
        """Restore placeholder text when entry loses focus"""
        if not self.message_entry.get(1.0, tk.END).strip():
            self.message_entry.insert(1.0, "Type your message here...")
            self.message_entry.config(fg="#999999")
            self.placeholder_active = True
    
    def on_enter_pressed(self, event):
        """Handle Enter key press in the message entry"""
        if event.state & 0x4:  # Ctrl key
            if not self.waiting_for_ai:
                self.send_message()
            return "break"
        
        if event.state & 0x1:  # Shift key
            return None
        
        if not self.waiting_for_ai:
            self.send_message()
        return "break"
    
    def get_message_text(self):
        """Get and clean the message text from the entry box"""
        raw_text = self.message_entry.get(1.0, tk.END)
        
        if "Type your message here..." in raw_text:
            raw_text = raw_text.replace("Type your message here...", "")
        
        clean_text = raw_text.strip()
        return clean_text
    
    def send_message(self):
        """Send the message from the input box to the conversation panel"""
        if self.waiting_for_ai:
            return
        
        message_text = self.get_message_text()
        
        if not message_text:
            self.message_entry.delete(1.0, tk.END)
            self.message_entry.insert(1.0, "Type your message here...")
            self.message_entry.config(fg="#999999")
            self.placeholder_active = True
            return
        
        current_time = datetime.now().strftime("%I:%M %p")
        
        # Add user message to conversation history
        self.conversation_history.append({
            "sender": "user",
            "message": message_text,
            "time": current_time
        })
        
        # Clear the input box and reset to placeholder
        self.message_entry.delete(1.0, tk.END)
        self.message_entry.insert(1.0, "Type your message here...")
        self.message_entry.config(fg="#999999")
        self.placeholder_active = True
        
        # Display updated conversation
        self.display_conversation()
        
        # Disable send button while processing
        self.waiting_for_ai = True
        self.send_button.config(state=tk.DISABLED, bg=self.button_disabled)
        
        # Add processing message
        self.add_processing_message()
        
        # Start processing in a separate thread
        ai_thread = threading.Thread(target=self.process_query, args=(message_text, current_time))
        ai_thread.daemon = True
        ai_thread.start()
    
    def add_processing_message(self):
        """Add a processing message to the conversation"""
        current_time = datetime.now().strftime("%I:%M %p")
        
        # Add processing message to conversation history
        self.conversation_history.append({
            "sender": "processing",
            "message": "Processing your query...",
            "time": current_time
        })
        
        # Display updated conversation
        self.display_conversation()
        
        # Store the processing message ID for updating
        self.processing_message_id = len(self.conversation_history) - 1
        self.processing_animation_index = 0
        
        # Start animation
        self.update_processing_animation()
    
    def update_processing_animation(self):
        """Update the processing animation"""
        if not self.waiting_for_ai or self.processing_message_id is None:
            return
        
        # Update the animation frame
        frame = self.processing_animation_frames[self.processing_animation_index]
        self.processing_animation_index = (self.processing_animation_index + 1) % len(self.processing_animation_frames)
        
        # Update the message in conversation history
        if self.processing_message_id < len(self.conversation_history):
            self.conversation_history[self.processing_message_id]["message"] = f"{frame} Processing your query..."
            self.display_conversation()
            
            # Schedule next animation update
            self.root.after(100, self.update_processing_animation)
    
    def process_query(self, query, user_message_time):
        """Process the query using query_search_entities.py"""
        try:
            # Import the query processor
            from query_search_entities import process_query_for_gui
            
            # Call the query processor
            result = process_query_for_gui(query)
            
            # Schedule UI update in main thread
            self.root.after(0, self.add_ai_response, result, user_message_time)
            
        except ImportError as e:
            error_message = f"Error importing query processor: {str(e)}"
            print(error_message)
            self.root.after(0, self.add_error_response, error_message, user_message_time)
        except Exception as e:
            error_message = f"Error processing query: {str(e)}"
            print(error_message)
            self.root.after(0, self.add_error_response, error_message, user_message_time)
    
    def add_error_response(self, error_message, user_message_time):
        """Add error response to conversation"""
        # Remove processing message
        if self.processing_message_id is not None:
            # Find and remove the processing message
            for i in range(len(self.conversation_history) - 1, -1, -1):
                if self.conversation_history[i]["sender"] == "processing":
                    del self.conversation_history[i]
                    break
        
        # Get current time for response
        ai_response_time = datetime.now().strftime("%I:%M %p")
        
        # Add error message
        self.conversation_history.append({
            "sender": "ai",
            "message": error_message,
            "time": ai_response_time
        })
        
        # Re-enable send button
        self.waiting_for_ai = False
        self.processing_message_id = None
        self.send_button.config(state=tk.NORMAL, bg=self.button_color)
        
        # Display updated conversation
        self.display_conversation()
        
        # Focus back to the message entry
        self.root.after(100, self.focus_message_entry)
    
    def add_ai_response(self, result_text, user_message_time):
        """Add AI response to conversation (called from main thread)"""
        # Remove processing message
        if self.processing_message_id is not None:
            # Find and remove the processing message
            for i in range(len(self.conversation_history) - 1, -1, -1):
                if self.conversation_history[i]["sender"] == "processing":
                    del self.conversation_history[i]
                    break
        
        # Get current time for AI response
        ai_response_time = datetime.now().strftime("%I:%M %p")
        
        # Clean up the result text if it contains the headers
        if "ELECTROLYTE RECOMMENDATION" in result_text:
            # Extract the relevant part
            lines = result_text.split('\n')
            start_idx = 0
            end_idx = len(lines)
            
            # Find the recommendation section
            for i, line in enumerate(lines):
                if "ELECTROLYTE RECOMMENDATION" in line:
                    start_idx = i + 2  # Skip the header line and the separator
                    break
            
            # Find the end of the recommendation
            for i in range(start_idx, len(lines)):
                if lines[i].strip() == "" and i > start_idx:
                    end_idx = i
                    break
            
            # Join the relevant lines
            result_text = '\n'.join(lines[start_idx:end_idx])
        
        # Add AI response to conversation history
        self.conversation_history.append({
            "sender": "ai",
            "message": result_text,
            "time": ai_response_time
        })
        
        # Re-enable send button
        self.waiting_for_ai = False
        self.processing_message_id = None
        self.send_button.config(state=tk.NORMAL, bg=self.button_color)
        
        # Display updated conversation
        self.display_conversation()
        
        # Focus back to the message entry for convenience
        self.root.after(100, self.focus_message_entry)
    
    def focus_message_entry(self):
        """Set focus to the message entry after AI response"""
        self.message_entry.focus_set()
        if self.placeholder_active:
            self.clear_placeholder()

def main():
    root = tk.Tk()
    app = ChatApplication(root)
    root.mainloop()

if __name__ == "__main__":
    main()