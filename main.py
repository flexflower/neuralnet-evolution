import matplotlib.pyplot as plt
import rules.cell_rules as cr
import rules.sim_rules as sr
import numpy as np
import inspect
import yaml

with open("params.yaml", "r") as f:
    params = yaml.safe_load(f)["one"]
    
params["mean_physics"] = np.array([
    params["mean_death"],
    params["mean_sex"],
    params["mean_strength"],
    params["mean_velocity"],
])

params["std_physics"] = np.array([
    params["std_death"],
    params["std_sex"],
    params["std_strength"],    
    params["std_velocity"],    
])

class Cell:
    def __init__(self):
        self.grid_size = params["grid_size"]
        self.alive = True
        self.age = 0
        self.phys_dna = np.random.normal(0, 1, (len(params["mean_physics"]))) * params["std_physics"] + params["mean_physics"]
        self.brain_dna = np.random.normal(0, 0.01, (params["num_actions"], params["num_sensors"]))
        self.death_age = self.phys_dna[0]
        self.sex = self.phys_dna[1].round()
        self.strength = self.phys_dna[2]
        self.velocity = self.phys_dna[3].round()
        self.pos = np.random.uniform(0, params["grid_size"]-1, 2).round()
        self.sensors = np.zeros((params["num_sensors"], 1))
        self.actions = np.zeros((params["num_actions"], 1))

    def live(self, clock, pos_map):
        self.move()
        self.update_sensors(clock, pos_map)
        self.think()
        self.age += 1
        if self.age >= self.death_age:
            self.alive = False

    def update_sensors(self, clock, pos_map):
        self.sensors = np.array([
            1,
            np.random.random(1).item(),
            np.sin(np.pi*clock/10).item(),
            self.pos[0] / self.grid_size,
            self.pos[1] / self.grid_size,
        ])

    def think(self):
        self.actions = (
            1 / (1 + np.exp(-1 * self.brain_dna @ self.sensors))).round()

    def move(self):
        self.pos = np.maximum.reduce(
            [np.minimum.reduce([self.pos + 
            (self.actions[:2].ravel() - self.actions[2:4].ravel()) * 
            self.velocity, np.ones(2)*(self.grid_size-1)]), np.zeros(2)]
        )
        
class Environment:
    def __init__(self):
        self.cellrule = "default"
        
        self.clock = 0
        self.size = params["grid_size"]
        self.ncell = params["n_cell"]
        self.grid = np.zeros((self.size, self.size), dtype=int)
        self.cells = [Cell() for _ in range(params["n_cell"])]
        self.pos_map = 0
        
    def __getattr__(self, attr):
        def callback(*args, **kwargs):
            return attr(*args, **kwargs)
            
        return callback

    def call_all(self, attr, *args, **kwargs):
        methods = [getattr(e, f"{attr}") for e in self.cells]
        return [method(*args, **kwargs) for method in methods]

    def update(self):
        if not np.any(self.cells):
            return 0
        
        self.call_all(self.cellrule, self.clock, self.pos_map)
        self.clock += 1
        self.call_all("think")
        self.cells = [c for c in self.cells if c.alive]
        return 1

    def get_grid(self):
        self.grid = np.zeros((self.size, self.size), dtype=int)
        self.pos_map = list(
            map(lambda cell: [int(cell.pos[0]), int(cell.pos[1])], self.cells))
        rows, cols = zip(*self.pos_map)
        self.grid[rows, cols] = 1

    def plotgrid(self):
        plt.title(f"Generation {self.clock}")
        plt.imshow(self.grid, interpolation="none", cmap="GnBu")
        plt.show()


class Simulation:
    def __init__(self, wsimrule="default", wcellrule="default"):
        simrules = inspect.getmembers(sr, inspect.isfunction) # Get all rules as functions
        self.simrule = next((r for r in simrules if r[0] == wsimrule), None) # Get the first object that matches the wanted simrule
        
        if self.simrule == None: raise AttributeError(f"{wsimrule} is not a valid simulation ruleset. [{', '.join(r[0] for r in simrules)}]")
        
        self.e = Environment() # Initialize the environment
        setattr(self.e, self.simrule[0], self.simrule[1]) # Bind the desired rule method to the environment
        
        # Almost the same steps as above
        cellrules = inspect.getmembers(cr, inspect.isfunction) 
        cellrule = next((r for r in cellrules if r[0] == wcellrule), None)
        
        if cellrule == None: raise AttributeError(f"{wcellrule} is not a valid cell ruleset. [{', '.join(r[0] for r in cellrules)}]")
        
        for c in self.e.cells:
            setattr(c, self.cellrule[0], self.cellrule[1])
            
        self.e.cellrule = cellrule
    
    def main(self):
        for i in range(params["num_sim"]):
            print("iteration n.", i)
            try:
                getattr(self.e, self.simrule[0])(self.e)
                self.e.get_grid()
                self.e.plotgrid()
                
            except ValueError as ve:
                print("Dead")
                break
            
        return 0

if __name__ == "__main__":
    s = Simulation()
    s.main()