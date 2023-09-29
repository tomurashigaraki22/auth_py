def countup(n):
    if n > 0:
        countdown(n)
    elif n == 0:
        print('Blastoff')
    else:
        print(n)
        countup(n+1)

def countdown(n): 
     if n <= 0: 
          print('Blastoff!') 
     else: 
          print(n) 
          countdown(n-1) 

number = input('Input number: ')
countup(int(number))