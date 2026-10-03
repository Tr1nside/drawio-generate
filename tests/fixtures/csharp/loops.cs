using System;

class Loops
{
    static void Main(string[] args)
    {
        int sum = 0;
        int i = 0;
        while (i < 10)
        {
            i++;
            if (i == 5)
            {
                continue;
            }
            if (i == 8)
            {
                break;
            }
            sum += i;
        }

        do
        {
            i--;
        } while (i > 0);

        int result = 0;
        for (int k = 0; k < 3; k++)
        {
            result += k;
        }

        foreach (var arg in args)
        {
            Console.WriteLine(arg);
        }

        Console.WriteLine(sum);
        Console.WriteLine(result);
    }
}
