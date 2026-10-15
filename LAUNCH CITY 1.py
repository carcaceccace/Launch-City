import math
import os
import random
import tkinter as tk
from PIL import Image, ImageTk

BASE_WIDTH, BASE_HEIGHT = 1000, 600
GRAVITY = 0.40
SKY_LIMIT = 30


class PhysicsLauncherGame:

  def __init__(self, root):
    self.root = root
    self.root.title("Physics Simulator - Projectile Motion & Math")

    self.root.geometry("1000x600")

    self.canvas = tk.Canvas(root, bg="#1e272e", highlightthickness=0)
    self.canvas.pack(fill=tk.BOTH, expand=True)

    self.game_state = "MENU"
    self.score_file = "high_scores.txt"
    self.load_leaderboard()

    self.camera_scroll = 0
    self.target_scroll = 0
    self.aiming = False
    self.score = 0
    self.current_building_idx = 0
    self.current_force = 0.0

    # Load PNG Background & Building assets if available
    try:
      self.bg_img_raw = Image.open("background.png")
    except Exception:
      self.bg_img_raw = None

    try:
      self.building_img_raw = Image.open("building.png")
    except Exception:
      self.building_img_raw = None

    # Performance Caching variables
    self.cached_bg_key = None
    self.tk_bg_image = None
    self.building_cache = {}
    self.ball_cache = {}
    self.last_sw, self.last_sh = 0, 0

    # THE 3 CASES (ARACHNE, NEMESIS, DANGO)
    self.roster = [
        (
            1.0,
            "#ff3f34",
            "Arachne (1.0kg)",
            0.0,
            {
                "idle": "small_idle.png",
                "launched": "small_launched.png",
                "landed": "small_landed.png",
            },
        ),
        (
            2.5,
            "#05c46b",
            "Nemesis (2.5kg)",
            0.72,
            {
                "idle": "medium_idle.png",
                "launched": "medium_launched.png",
                "landed": "medium_landed.png",
            },
        ),
        (
            5.0,
            "#34e7e4",
            "Dango (5.0kg)",
            0.50,
            {
                "idle": "large_idle.png",
                "launched": "large_launched.png",
                "landed": "large_landed.png",
            },
        ),
    ]
    self.char_idx = 0

    # Bind Controls
    self.canvas.bind("<ButtonPress-1>", self.handle_click)
    self.canvas.bind("<B1-Motion>", self.adjust_aiming)
    self.canvas.bind("<ButtonRelease-1>", self.launch)
    self.canvas.bind("<Configure>", lambda e: self.draw_everything())

    self.setup_buildings()
    self.game_loop()

  def load_leaderboard(self):
    self.high_scores = []
    if os.path.exists(self.score_file):
      try:
        with open(self.score_file, "r") as f:
          for line in f:
            if line.strip().isdigit():
              self.high_scores.append(int(line.strip()))
      except:
        pass
    self.high_scores.sort(reverse=True)
    self.high_scores = self.high_scores[:5]

  def save_score(self):
    self.high_scores.append(self.score)
    self.high_scores.sort(reverse=True)
    self.high_scores = self.high_scores[:5]
    try:
      with open(self.score_file, "w") as f:
        for s in self.high_scores:
          f.write(f"{s}\n")
    except:
      pass

  def setup_buildings(self):
    self.buildings = [{"x": 80, "y": 420, "w": 140, "h": 180}]
    last_x = 80

    for _ in range(120):
      gap = random.randint(180, 280)
      width = random.randint(110, 150)
      height = random.randint(200, 380)
      last_x += gap + 50
      self.buildings.append(
          {"x": last_x, "y": BASE_HEIGHT - height, "w": width, "h": height}
      )

  def spawn_character(self):
    mass, color, name, slide, sprites = self.roster[self.char_idx]
    self.char_mass = mass
    self.char_color = color
    self.char_name = name
    self.char_slide = slide
    self.char_sprites = sprites

    self.char_radius = 36 + int(mass * 3.0)

    self.char_raw_images = {}
    for state, filename in self.char_sprites.items():
      try:
        self.char_raw_images[state] = Image.open(filename)
      except Exception:
        self.char_raw_images[state] = None

    current_b = self.buildings[self.current_building_idx]
    self.char_spawn_x = current_b["x"] + current_b["w"] // 2
    self.char_spawn_y = current_b["y"] - self.char_radius

    self.char_x = self.char_spawn_x
    self.char_y = self.char_spawn_y
    self.char_vx = 0
    self.char_vy = 0
    self.is_launched = False
    self.is_sliding = False
    self.current_force = 0.0

  def handle_click(self, event):
    sw = self.canvas.winfo_width()
    sh = self.canvas.winfo_height()

    if self.game_state == "PLAYING":
      if not self.is_launched and not self.is_sliding:
        self.aiming = True
        self.mx, self.my = event.x, event.y

    elif self.game_state == "MENU" or self.game_state == "GAMEOVER":
      center_x = sw // 2
      btn_w, btn_h = 160, 50
      btn_y1 = int(sh * 0.73)
      btn_y2 = btn_y1 + btn_h

      if btn_y1 <= event.y <= btn_y2:
        if (center_x - 240) <= event.x <= (center_x - 80):
          self.start_new_run(0)
        elif (center_x - 80) <= event.x <= (center_x + 80):
          self.start_new_run(1)
        elif (center_x + 80) <= event.x <= (center_x + 240):
          self.start_new_run(2)

  def adjust_aiming(self, event):
    if self.game_state == "PLAYING" and self.aiming:
      self.mx, self.my = event.x, event.y
      sw = self.canvas.winfo_width()
      sh = self.canvas.winfo_height()

      scale_x = sw / BASE_WIDTH
      scale_y = sh / BASE_HEIGHT

      screen_char_x = (self.char_x - self.camera_scroll) * scale_x
      screen_char_y = self.char_y * scale_y
      dist = math.hypot(self.mx - screen_char_x, self.my - screen_char_y)
      self.current_force = min((dist / scale_x) * 0.75, 200.0)

  def launch(self, event):
    if self.game_state == "PLAYING" and self.aiming:
      self.aiming = False
      sw = self.canvas.winfo_width()
      sh = self.canvas.winfo_height()

      scale_x = sw / BASE_WIDTH
      scale_y = sh / BASE_HEIGHT

      screen_char_x = (self.char_x - self.camera_scroll) * scale_x
      screen_char_y = self.char_y * scale_y
      dx = self.mx - screen_char_x
      dy = self.my - screen_char_y
      angle = math.atan2(dy, dx)
      dist = math.hypot(dx, dy)

      applied_force = min((dist / scale_x) * 0.75, 200.0)
      launch_speed = (applied_force / self.char_mass) * 0.42

      self.char_vx = launch_speed * math.cos(angle)
      self.char_vy = launch_speed * math.sin(angle)
      self.is_launched = True

  def start_new_run(self, selected_idx):
    self.score = 0
    self.current_building_idx = 0
    self.camera_scroll = 0
    self.target_scroll = 0
    self.char_idx = selected_idx
    self.setup_buildings()
    self.spawn_character()
    self.game_state = "PLAYING"

  def game_loop(self):
    if self.game_state == "PLAYING":
      self.camera_scroll += (self.target_scroll - self.camera_scroll) * 0.08

      if self.is_launched:
        self.char_vy += GRAVITY
        self.char_x += self.char_vx
        self.char_y += self.char_vy

        if self.char_y > BASE_HEIGHT + 50 or self.char_y < SKY_LIMIT:
          self.save_score()
          self.game_state = "GAMEOVER"
        else:
          for idx, b in enumerate(self.buildings):
            if b["x"] - 5 <= self.char_x + self.char_radius <= b["x"] + 10:
              if self.char_y + self.char_radius > b["y"] + 10:
                self.char_vx = -self.char_vx * 0.3

            if b["x"] <= self.char_x <= b["x"] + b["w"]:
              if (
                  b["y"] <= self.char_y + self.char_radius <= b["y"] + 16
                  and self.char_vy > 0
              ):
                self.char_y = b["y"] - self.char_radius
                self.char_vy = 0
                self.is_launched = False

                if idx > self.current_building_idx:
                  self.score += idx - self.current_building_idx
                  self.current_building_idx = idx

                if abs(self.char_vx) > 0.5 and self.char_slide > 0:
                  self.is_sliding = True
                else:
                  self.lock_position(b)
                break

      elif self.is_sliding:
        self.char_vx *= self.char_slide
        self.char_x += self.char_vx
        current_b = self.buildings[self.current_building_idx]

        if not (
            current_b["x"] <= self.char_x <= current_b["x"] + current_b["w"]
        ):
          self.is_sliding = False
          self.is_launched = True
        elif abs(self.char_vx) < 0.2:
          self.is_sliding = False
          self.lock_position(current_b)

    self.draw_everything()
    self.root.after(16, self.game_loop)

  def lock_position(self, building):
    self.char_vx = 0
    building_center = building["x"] + building["w"] // 2
    self.target_scroll = building_center - 160
    self.char_spawn_x = self.char_x
    self.char_spawn_y = self.char_y
    self.current_force = 0.0

  def draw_everything(self):
    self.canvas.delete("all")
    sw = self.canvas.winfo_width()
    sh = self.canvas.winfo_height()
    if sw <= 1 or sh <= 1:
      return

    if (sw, sh) != (self.last_sw, self.last_sh):
      self.building_cache.clear()
      self.ball_cache.clear()
      self.last_sw, self.last_sh = sw, sh
      self.cached_bg_key = None

    scale_x = sw / BASE_WIDTH
    scale_y = sh / BASE_HEIGHT

    # 1. RENDER BACKGROUND
    bg_key = (sw, sh)
    if bg_key != self.cached_bg_key:
      if self.bg_img_raw:
        resized_bg = self.bg_img_raw.resize(
            (max(1, sw), max(1, sh)), Image.Resampling.LANCZOS
        )
        self.tk_bg_image = ImageTk.PhotoImage(resized_bg)
      self.cached_bg_key = bg_key

    if self.tk_bg_image:
      self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_bg_image)
    else:
      self.canvas.create_rectangle(0, 0, sw, sh, fill="#1e272e", outline="")

    # Atmosphere limit line
    self.canvas.create_line(
        0,
        SKY_LIMIT * scale_y,
        sw,
        SKY_LIMIT * scale_y,
        fill="#ff3f34",
        width=2,
        dash=(6, 4),
    )
    self.canvas.create_text(
        sw - 15,
        (SKY_LIMIT + 8) * scale_y,
        anchor="e",
        text="OUT OF ATMOSPHERE ZONE",
        font=("Arial", int(8 * scale_y), "bold"),
        fill="#ff3f34",
    )

    # 2. RENDER BUILDINGS
    for b in self.buildings:
      screen_x = (b["x"] - self.camera_scroll) * scale_x
      if -200 < screen_x < sw + 200:
        bw_scaled = int(b["w"] * scale_x)
        bh_scaled = int((BASE_HEIGHT - b["y"]) * scale_y)

        if self.building_img_raw:
          cache_key = (bw_scaled, bh_scaled)
          if cache_key not in self.building_cache:
            res_building = self.building_img_raw.resize(
                (max(1, bw_scaled), max(1, bh_scaled)), Image.Resampling.LANCZOS
            )
            self.building_cache[cache_key] = ImageTk.PhotoImage(res_building)

          tk_b_img = self.building_cache[cache_key]
          self.canvas.create_image(
              screen_x, b["y"] * scale_y, anchor=tk.NW, image=tk_b_img
          )
        else:
          self.canvas.create_rectangle(
              screen_x,
              b["y"] * scale_y,
              screen_x + bw_scaled,
              sh,
              fill="#485460",
              outline="#05c46b",
              width=3,
          )

    # 3. AIMING TRAJECTORY SIMULATION
    if self.game_state == "PLAYING" and self.aiming:
      screen_char_x = (self.char_x - self.camera_scroll) * scale_x
      screen_char_y = self.char_y * scale_y
      self.canvas.create_line(
          screen_char_x,
          screen_char_y,
          self.mx,
          self.my,
          fill="#ffffff",
          width=2,
          dash=(4, 2),
      )

      sim_x, sim_y = self.char_x - self.camera_scroll, self.char_y
      dx = (self.mx / scale_x) - sim_x
      dy_true = (self.my / scale_y) - sim_y
      angle = math.atan2(dy_true, dx)
      dist = math.hypot(dx, dy_true)

      sim_force = min(dist * 0.75, 200.0)
      sim_speed = (sim_force / self.char_mass) * 0.42
      sim_vx = sim_speed * math.cos(angle)
      sim_vy = sim_speed * math.sin(angle)

      for _ in range(45):
        sim_vy += GRAVITY
        sim_x += sim_vx
        sim_y += sim_vy
        if sim_y > BASE_HEIGHT or sim_y < SKY_LIMIT:
          break
        self.canvas.create_oval(
            (sim_x - 2) * scale_x,
            (sim_y - 2) * scale_y,
            (sim_x + 2) * scale_x,
            (sim_y + 2) * scale_y,
            fill="#ffdd59",
        )

    # 4. ACTIVE CHARACTER & SIMPLE DISTANCE HUD
    if self.game_state == "PLAYING":
      screen_cx = (self.char_x - self.camera_scroll) * scale_x
      screen_cy = self.char_y * scale_y

      ball_scale = scale_y
      rx = self.char_radius * ball_scale
      ry = self.char_radius * ball_scale

      if self.is_launched:
        active_state = "launched"
      elif self.is_sliding:
        active_state = "landed"
      else:
        if self.score > 0:
          active_state = "landed"
        else:
          active_state = "idle"

      raw_img = self.char_raw_images.get(active_state)

      if raw_img:
        diameter = max(1, int(rx * 2))
        ball_key = (self.char_idx, active_state, diameter)

        if ball_key not in self.ball_cache:
          res_ball = raw_img.resize(
              (diameter, diameter), Image.Resampling.LANCZOS
          )
          self.ball_cache[ball_key] = ImageTk.PhotoImage(res_ball)

        tk_ball_img = self.ball_cache[ball_key]
        self.canvas.create_image(
            screen_cx, screen_cy, anchor=tk.CENTER, image=tk_ball_img
        )
      else:
        self.canvas.create_oval(
            screen_cx - rx,
            screen_cy - ry,
            screen_cx + rx,
            screen_cy + ry,
            fill=self.char_color,
            outline="#ffffff",
            width=2,
        )

      bar_width = int(self.current_force * 1.0 * scale_x)

      self.canvas.create_rectangle(
          sw - int(250 * scale_x),
          int(25 * scale_y),
          sw - int(48 * scale_x),
          int(45 * scale_y),
          outline="white",
          width=2,
      )
      if bar_width > 0:
        self.canvas.create_rectangle(
            sw - int(248 * scale_x),
            int(27 * scale_y),
            sw - int(248 * scale_x) + bar_width,
            int(43 * scale_y),
            fill="#ffdd59",
            outline="",
        )
      self.canvas.create_text(
          sw - int(260 * scale_x),
          int(35 * scale_y),
          anchor="e",
          text=f"FORCE: {self.current_force:.1f} N",
          font=("Impact", int(14 * scale_y)),
          fill="#ffdd59",
      )

      # --- SIMPLE DISTANCE TO NEXT BUILDING ---
      distance_text = "Next Gap: End of Course"
      next_idx = self.current_building_idx + 1
      if next_idx < len(self.buildings):
        current_b = self.buildings[self.current_building_idx]
        next_b = self.buildings[next_idx]
        gap_distance = next_b["x"] - (current_b["x"] + current_b["w"])
        distance_text = f"Next Gap: {gap_distance}m"

      # Educational HUD Display
      self.canvas.create_text(
          int(25 * scale_x),
          int(25 * scale_y),
          anchor="nw",
          text=f"SCORE: {self.score}",
          font=("Impact", int(28 * scale_y)),
          fill="#05c46b",
      )
      self.canvas.create_text(
          int(25 * scale_x),
          int(65 * scale_y),
          anchor="nw",
          text=f"Projectile: {self.char_name}",
          font=("Arial", int(11 * scale_y), "bold"),
          fill="#fff",
      )
      self.canvas.create_text(
          int(25 * scale_x),
          int(90 * scale_y),
          anchor="nw",
          text=distance_text,
          font=("Arial", int(10 * scale_y), "bold"),
          fill="#ffdd59",
      )

    # 5. OVERLAY STATE MENUS
    if self.game_state == "MENU":
      if not self.bg_img_raw:
        self.canvas.create_rectangle(0, 0, sw, sh, fill="#1e272e", outline="")
      self.canvas.create_text(
          sw // 2,
          int(120 * scale_y),
          text="PRODUCED PHYSICS LAUNCHER",
          font=("Impact", int(42 * scale_y)),
          fill="#05c46b",
      )
      self.canvas.create_text(
          sw // 2,
          int(180 * scale_y),
          text="SELECT YOUR PROJECTILE TO BEGIN:",
          font=("Arial", int(14 * scale_y), "bold"),
          fill="white",
      )
      self.draw_buttons(sw, sh, scale_x, scale_y)

    elif self.game_state == "GAMEOVER":
      self.canvas.create_rectangle(0, 0, sw, sh, fill="#000000", stipple="gray50")
      self.canvas.create_text(
          sw // 2,
          int(80 * scale_y),
          text="GAME OVER",
          font=("Impact", int(44 * scale_y)),
          fill="#ff3f34",
      )
      self.canvas.create_text(
          sw // 2,
          int(130 * scale_y),
          text=f"YOUR SCORE: {self.score}",
          font=("Arial", int(16 * scale_y), "bold"),
          fill="white",
      )
      self.canvas.create_text(
          sw // 2,
          int(180 * scale_y),
          text="🏆 LOCAL TOP 5 HIGH SCORES 🏆",
          font=("Arial", int(12 * scale_y), "bold"),
          fill="#ffdd59",
      )

      start_y = 210
      for rank, s in enumerate(self.high_scores):
        prefix = "⭐ " if rank == 0 else f"{rank + 1}. "
        self.canvas.create_text(
            sw // 2,
            int(start_y * scale_y),
            text=f"{prefix}{s} Buildings Cleared",
            font=("Arial", int(11 * scale_y)),
            fill="#d2dae2",
        )
        start_y += 24

      self.canvas.create_text(
          sw // 2,
          int(385 * scale_y),
          text="PLAY AGAIN? SELECT NEXT BALL CLASS:",
          font=("Arial", int(13 * scale_y), "bold"),
          fill="white",
      )
      self.draw_buttons(sw, sh, scale_x, scale_y)

  def draw_buttons(self, sw, sh, scale_x, scale_y):
    center_x = sw // 2
    btn_y1 = int(sh * 0.73)
    btn_y2 = btn_y1 + int(50 * scale_y)

    # Button 1: Arachne
    self.canvas.create_rectangle(
        center_x - int(240 * scale_x),
        btn_y1,
        center_x - int(80 * scale_x),
        btn_y2,
        fill="#ff3f34",
        outline="white",
        width=2,
    )
    self.canvas.create_text(
        center_x - int(160 * scale_x),
        (btn_y1 + btn_y2) // 2,
        text="ARACHNE (1.0kg)",
        font=("Arial", int(11 * scale_y), "bold"),
        fill="white",
    )

    # Button 2: Nemesis
    self.canvas.create_rectangle(
        center_x - int(80 * scale_x),
        btn_y1,
        center_x + int(80 * scale_x),
        btn_y2,
        fill="#05c46b",
        outline="white",
        width=2,
    )
    self.canvas.create_text(
        center_x,
        (btn_y1 + btn_y2) // 2,
        text="NEMESIS (2.5kg)",
        font=("Arial", int(11 * scale_y), "bold"),
        fill="white",
    )

    # Button 3: Dango
    self.canvas.create_rectangle(
        center_x + int(80 * scale_x),
        btn_y1,
        center_x + int(240 * scale_x),
        btn_y2,
        fill="#34e7e4",
        outline="white",
        width=2,
    )
    self.canvas.create_text(
        center_x + int(160 * scale_x),
        (btn_y1 + btn_y2) // 2,
        text="DANGO (5.0kg)",
        font=("Arial", int(11 * scale_y), "bold"),
        fill="black",
    )


if __name__ == "__main__":
  root = tk.Tk()
  game = PhysicsLauncherGame(root)
  root.mainloop()