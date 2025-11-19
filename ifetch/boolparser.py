import argparse  
 
# source: https://www.pythontutorials.net/blog/parsing-boolean-values-with-argparse/

class BooleanAction(argparse.Action):  
    def __call__(self, parser, namespace, value, option_string=None):  
        if value is None:  
            # If --flag is passed without a value, use const  
            setattr(namespace, self.dest, self.const)  
            return  
        if value is True:
            setattr(namespace, self.dest, self.const)  
        elif value is False:
            setattr(namespace, self.dest, self.const)  
        else:
            lower_value = value.lower()  
            if lower_value in ('true', 't', 'yes', 'y', '1'):  
                setattr(namespace, self.dest, True)  
            elif lower_value in ('false', 'f', 'no', 'n', '0'):  
                setattr(namespace, self.dest, False)  
            else:  
                raise argparse.ArgumentTypeError(  
                    f"Invalid boolean value: {value}. Use: true/false, t/f, yes/no, y/n, 1/0"  
                )  
 